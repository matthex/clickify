import requests, re, random, psycopg2, json
from lxml import html

name = 'lottosumo'

def init():
    global base_url
    global config

    #get config from heroku config vars
    config = json.loads(os.environ[name])
    base_url = config['base_url']

def harvest():
    #session
    session = requests.Session()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 6.3; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2272.101 Safari/537.36",
    }

    #login to get session and token
    token = login(session)

    #get ticket page
    ticket_page = session.get(base_url + "lotto/spielscheine").text

    #claim wins
    claim_wins(session, ticket_page)

    #get main page
    main_page = session.get(base_url).text

    #get ticket information
    ticket_count = get_ticket_count(main_page)
    current_lottery_date = get_current_lottery_date(main_page)
    current_lottery_ticket_count = get_ticket_count_for_current_lottery(current_lottery_date, ticket_page)

    #place tickets
    played_tickets = 0
    while current_lottery_ticket_count < 10 and ticket_count > 0:
        play_lottery(session, token)
        current_lottery_ticket_count += 1
        ticket_count -= 1
        played_tickets += 1

    return played_tickets

def login(session):
    login_url = base_url + "user/login"
    login_page = session.get(login_url)

    #get token
    xml = html.fromstring(login_page.text)
    token = xml.xpath('//input[@name="_token"]/@value')[0]

    #login information
    email = config['email']
    password = config['password']

    #create post data
    post_data = [
        ('_token', token),
        ('email', email),
        ('password', password),
        ('remember', '0'),
    ]

    #actual login
    login_page = session.post(login_url, data=post_data)

    return token

def claim_wins(session, html):
    #get links to wins
    links = re.findall('https:\/\/lottosumo\.de\/lotto\/gewinn\/\d+', html)

    for link in links:
        #get page of win
        win_page = session.get(link).text

        #get win info
        win = re.search('<h4>(.*)<\/h4>', win_page)[1]
        
        #get token
        token = re.search('hidden" value="(\w+)"', win_page)[1]

        #create post data
        post_data = [
            ('_token', token)
        ]

        #redeem
        session.post(base_url + "lotto/gewinn/einloesen", data=post_data)

def get_ticket_count(html):
    match = re.search('Sumo Credits:\s<span\sclass="">(\d*)', html)
    return int(match[1])

def get_current_lottery_date(html):
    match = re.search('<p>\w\w,\s*(\d{1,2}\.\s\w+)', html)
    return match[1]

def get_ticket_count_for_current_lottery(date, html):
    html = html.replace("\r", '').replace("\n", '')
    match = re.search('<div class="row">\s*<h2>Ziehung\s\w\w\,\s*' + date + '<\/h2>\s*(.*)<!--\/.row-->', html)
    if match == None:
        return 0
    else:
        return len(re.findall('/Schein-Nummer/', match[1]))

def play_lottery(session, token):
    #generate numbers
    numbers = sorted(random.sample(range(1,49), 6))
    special_number = random.randint(0,9)

    #create post data
    post_data = [
        ('_token', token),
        ('numbers', ",".join(str(x) for x in numbers)),
        ('special_number', special_number)
    ]

    #play
    session.post(base_url + "lotto/spielen", data=post_data)

def logfile(text):
    f = open('logfile', 'w')
    f.write(text)
    f.close()

if __name__ == '__main__':
    init()
    harvest()