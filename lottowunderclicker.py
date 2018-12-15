import requests, re, datetime, random, psycopg2, json
from lxml import html
from os import environ

name = "lottowunder"

def init():
    global base_url
    global config

    #get config from heroku config vars
    config = json.loads(environ[name])
    base_url = config['base_url']

def harvest():
    #session
    session = requests.Session()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 6.3; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2272.101 Safari/537.36",
    }
    session.headers = headers

    #login to get session and token
    token = login(session)

    #get ticket page
    ticket_page = session.get(base_url + "scheine").text

    #claim wins
    claim_wins(session, ticket_page)

    #claim cards
    card_page = session.get(base_url + "rubbellose").text
    claim_cards(token, session, card_page)

    #get main page
    main_page = session.get(base_url).text

    #get ticket information
    credit_count = get_credit_count(main_page)
    booster_count = get_booster_count(main_page)
    wonderstar_count = get_wonderstar_count(main_page)
    current_lottery_date = str(datetime.date.today().day) + " " + convert_month(datetime.date.today().month)
    current_lottery_ticket_count = get_ticket_count_for_current_lottery(current_lottery_date, ticket_page)

    ticket_maximum = 10

    #activate wonderstar
    if wonderstar_count > 0:
        session.get(base_url + "wunderstern")
        ticket_maximum = 15

    #place tickets
    played_tickets = 0
    while current_lottery_ticket_count < ticket_maximum and credit_count > 0:
        if booster_count > 0:
            play_lottery(session, token, True)
            booster_count -= 1
        else:
            play_lottery(session, token)
        current_lottery_ticket_count += 1
        credit_count -= 1
        played_tickets += 1
    
    return played_tickets

def login(session):
    login_url = base_url + "login"
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
        ('password', password)
    ]

    #actual login
    login_page = session.post(login_url, data=post_data)

    return token

def claim_wins(session, html):
    html = html.replace("\r", '').replace("\n", '').replace(" ", "")

    #get win tickets information
    win_tickets = re.findall('<formclass="frmRedeem"role="form"method="post"ticket-id="\d+"><inputtype="hidden"name="_token"value="(\w+)"><inputtype="hidden"name="redeem_ticket"value="(\d+)"><buttonid="redeem\d+"type="submit"class="btnbtn-successbtn-sm">Gewinneinlösen<\/button><\/form>', html)

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

def claim_cards(token, session, html):
    cards = re.findall('https:\/\/lottowunder\.com\/rubbellos\/spielen\/(\d+)', html)
    for card in cards:
        #create post data
        post_data = [
            ('_token', token),
            ('card_id', card)
        ]
        #redeem
        session.post(base_url + "rubbellos/einloesen?id=" + card, data=post_data)

def get_credit_count(html):
    match = re.search('&nbsp;<img src=\'https:\/\/lottowunder\.com\/assets\/img\/credit\.png\' alt=\'Wunder Dollar ist eine virtuelle und kostenlose Währung, die zum Spielen benötigt wird\.\'  style=\'width: 20px\' title=\'Wunder Dollar ist eine virtuelle und kostenlose Währung, die zum Spielen benötigt wird\.\' rel=\'tooltip\' \/>&nbsp;(\d*)', html)
    if not match:
        return 0
    else:
        return int(match[1])

def get_booster_count(html):
    match = re.search('&nbsp;<img src=\'https:\/\/lottowunder\.com\/assets\/img\/booster\.png\' alt=\'Mit Wunder Booster kannst du deine Wunder Doller Gewinne verdoppeln!\'  style=\'width: 20px\' title=\'Mit Wunder Booster kannst du deine Wunder Doller Gewinne verdoppeln!\' rel=\'tooltip\' \/>&nbsp;(\d*)', html)
    if not match:
        return 0
    else:
        return int(match[1])

def get_wonderstar_count(html):
    match = re.search('&nbsp;<img src=\'https:\/\/lottowunder\.com\/assets\/img\/star\.png\' alt=\'Aktiviere einen Wunder Stern um mehr Spielscheine zu spielen!\'  style=\'width: 20px\' title=\'Aktiviere einen Wunder Stern um mehr Spielscheine zu spielen!\' rel=\'tooltip\' \/>&nbsp;(\d*)', html)
    if not match:
        return 0
    else:
        return int(match[1])

def get_ticket_count_for_current_lottery(date, html):
    html = html.replace("\r", '').replace("\n", '')
    match = re.search('<h4>Ziehung\s\w\w\s*' + date + '<\/h4>(.*)<div class="tab-pane', html)
    if not match:
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

def convert_month(month):
  return {
        1: "Jan",
        2: "Feb",
        3: "Mär",
        4: "Apr",
        5: "Mai",
        6: "Jun",
        7: "Jul",
        8: "Aug",
        9: "Sep",
        10: "Okt",
        11: "Nov",
        12: "Dez"
    }.get(month, "Err")

if __name__ == '__main__':
    init()
    harvest()