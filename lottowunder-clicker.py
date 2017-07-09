import requests, re, datetime, locale, random, psycopg2, json
from lxml import html

name = "lottowunder"

def init():
    global base_url
    global db_id
    global conn
    global cur

    #get db connection info
    with open('config.json') as json_data_file:
        config = json.load(json_data_file)

    #connect to db
    conn = psycopg2.connect("dbname='" + config['db-conn']['db'] + "' user='" + config['db-conn']['user'] + "' host='" + config['db-conn']['host'] + "' password='" + config['db-conn']['password'] + "'")
    cur = conn.cursor()

    #get url
    cur.execute("SELECT id, url FROM clickify.sites WHERE name='" + name + "'") 
    result = cur.fetchone()
    db_id = result[0]
    base_url = result[1]

def harvest():
    #session
    session = requests.Session()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 6.3; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2272.101 Safari/537.36",
    }

    #login to get session and token
    token = login(session)

    #get ticket page
    ticket_page = session.get(base_url + "scheine").text

    #claim wins
    claim_wins(session, ticket_page)

    #get main page
    main_page = session.get(base_url).text

    #get ticket information
    credit_count = get_credit_count(main_page)
    booster_count = get_booster_count(main_page)
    locale.setlocale(locale.LC_ALL, 'deu_deu')
    current_lottery_date = datetime.date.today().strftime("%d %b").lstrip('0')
    current_lottery_ticket_count = get_ticket_count_for_current_lottery(current_lottery_date, ticket_page)

    #place tickets
    while current_lottery_ticket_count < 10 and credit_count >0:
        if booster_count > 0:
            play_lottery(session, token, True)
            booster_count -= 1
        else:
            play_lottery(session, token)
        current_lottery_ticket_count += 1
        credit_count -= 1

def login(session):
    login_url = base_url + "login"
    login_page = session.get(login_url)

    #get token
    xml = html.fromstring(login_page.text)
    token = xml.xpath('//input[@name="_token"]/@value')[0]

    #login information
    cur.execute("SELECT username, password FROM clickify.logins WHERE site_id =" + str(db_id))
    result = cur.fetchone()
    email = result[0]
    password = result[1]

    #create post data
    post_data = [
        ('_token', token),
        ('email', email),
        ('password', password)
    ]

    #actual login
    login_page = session.post(login_url, data=post_data)

    return token

def claim_wins(session, html):
    html = html.replace("\r", '').replace("\n", '').replace(" ", "")

    #get win tickets information
    win_tickets = re.findall('<formclass="frmRedeem"role="form"method="post"><inputtype="hidden"name="_token"value="(\w+)"><inputtype="hidden"name="redeem_ticket"value="(\d+)"><buttonid="redeem\d+"type="submit"class="btnbtn-successbtn-xs">Gewinneinlösen<\/button><\/form>', html)

    for win_ticket in win_tickets:
        win = "win"
        token = win_ticket[0]
        ticket_id = win_ticket[1]

        #create post data
        post_data = [
            ('_token', token),
            ('redeem_ticket', ticket_id)
        ]

        #redeem
        session.post(base_url + "gewinn/einloesen", data=post_data)

        #store win in DB
        cur.execute("INSERT INTO clickify.wins (win, date, site_id) VALUES ('" + win + "', now()," + str(db_id) + ")")
        conn.commit()

def get_credit_count(html):
    match = re.search('(\d*)&nbsp;<img src=\'https:\/\/lottowunder\.com\/assets\/img\/credit\.png', html)
    return int(match[1])

def get_booster_count(html):
    match = re.search('(\d*)&nbsp;<img src=\'https:\/\/lottowunder\.com\/assets\/img\/booster\.png', html)
    return int(match[1])

def get_ticket_count_for_current_lottery(date, html):
    html = html.replace("\r", '').replace("\n", '')
    match = re.search('<h4>Ziehung\s\w\w\s*' + date + '<\/h4>(.*)<div class="tab-pane', html)
    if match == None:
        return 0
    else:
        return len(re.findall('lotto_balls', match[1]))

def play_lottery(session, token, boost = False):
    #generate numbers
    numbers = sorted(random.sample(range(1,49), 6))
    special_number = random.randint(0,9)

    #create post data
    post_data = [
        ('_token', token),
        ('numbers', ",".join(str(x) for x in numbers)),
        ('special_number', special_number),
    ]
    if boost:
        post_data.append(('booster', 1))
    #play
    session.post(base_url + "play", data=post_data)

def logfile(text):
    f = open('logfile', 'w')
    f.write(text)
    f.close()

if __name__ == '__main__':
    init()
    harvest()