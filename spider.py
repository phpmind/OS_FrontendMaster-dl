from bs4 import BeautifulSoup
from config import ACCOUNT
from selenium import webdriver
from urllib2 import urlopen, URLError, HTTPError
import cookielib
import json
import mechanize
import os
import string
import time

# Browser setup
cookiejar = cookielib.CookieJar()
browser = mechanize.Browser()
browser.set_cookiejar(cookiejar)

# Selenium browser setup
chrome = webdriver.Chrome()


def login(username, password, browser=browser):
    BASE_URL = 'https://frontendmasters.com/login/'
    browser.open(BASE_URL)

    # Select the first form
    browser.select_form(nr=0)
    browser.form['rcp_user_login'] = username
    browser.form['rcp_user_pass'] = password
    browser.submit()

    return browser


def get_course_list(browser=browser):
    bs_course_page = BeautifulSoup(browser.response().read(), "html.parser")
    course_titles = bs_course_page.find_all('h2')
    course_links = []

    for title in course_titles:
        link = title.find('a')

        if link is not None:
            course = {'title': link.getText(), 'url': link['href']}

            course_links.append(course)

    return course_links


def get_videos_data(videos_section_items):
    subsections = []

    for video in videos_section_items:
        # Course subsection data structure
        course_subsection = {
            'title': None,
            'url': None,
            'downloadable_url': None
        }

        course_subsection['url'] = video.find('a')['href']
        course_subsection['title'] = video.find('a').find(
            'span', {'class', 'text'}
        ).find(
            'span', {'class', 'title'}
        ).getText()

        subsections.append(course_subsection)

    return subsections


def get_section_data(sections_items):
    sections = []

    for item in sections_items:
        # Course section data structure
        course_section = {'title': None, 'subsections': []}

        course_section['title'] = item.find(
            'h4', {'class': 'video-nav-section-title'}
        ).getText()

        videos_section = item.find('ul')
        videos_section_items = videos_section.find_all('li')

        videos_data = get_videos_data(videos_section_items)
        course_section['subsections'].extend(videos_data)

        sections.append(course_section)

    return sections


def get_detailed_course_list(course_list, browser=browser):
    detailed_course_list = []

    for course in course_list:
        # Course detail data structure
        course_detial = {'title': None, 'url': None, 'sections': []}

        course_detial['url'] = course['url']
        course_detial['title'] = course['title']

        browser.open(course_detial['url'])
        soup_page = BeautifulSoup(browser.response().read(), 'html.parser')

        # Find video nav list
        sections = soup_page.find('ul', {'class': 'video-nav-list'})
        sections_items = sections.find_all(
            'li', {'class': 'video-nav-section'}
        )

        sections = get_section_data(sections_items)
        course_detial['sections'].extend(sections)

        detailed_course_list.append(course_detial)

    return detailed_course_list


def download_file(url, path):

    if not os.path.isfile(path):
        print url
        buff = urlopen(url)
        print "Downloading: %s" % (path)

        with open(path, 'wb') as local_file:
            local_file.write(buff.read())


def format_filename(s):
    """Take a string and return a valid filename constructed from the string.
Uses a whitelist approach: any characters not present in valid_chars are
removed. Also spaces are replaced with underscores.

Note: this method may produce invalid filenames such as ``, `.` or `..`
When I use this method I prepend a date string like '2009_01_15_19_46_32_'
and append a file extension like '.txt', so I avoid the potential of using
an invalid filename.

"""
    valid_chars = "-_.() %s%s" % (string.ascii_letters, string.digits)
    filename = ''.join(c for c in s if c in valid_chars)
    filename = filename.replace(' ', '_')  # I don't like spaces in filenames.
    return filename


def save_data():
    # Browser with all login info.
    browser = login(ACCOUNT['username'], ACCOUNT['password'])

    with open('DATA.json', 'w') as file:
        course_list = get_course_list()
        detailed_course_list = get_detailed_course_list(course_list)
        file.write(json.dumps(detailed_course_list))


def load_data(path):
    with open(path, 'r') as file:
        return json.loads(file.read())


def real_browser_login(chrome=chrome):
    URL_LOGIN = 'https://frontendmasters.com/login/'
    chrome.get(URL_LOGIN)
    time.sleep(2)

    username = chrome.find_element_by_id('rcp_user_login')
    username.send_keys(ACCOUNT['username'])
    password = chrome.find_element_by_id('rcp_user_pass')
    password.send_keys(ACCOUNT['password'])

    time.sleep(2)
    chrome.find_element_by_id('rcp_login_submit').click()


def get_video_source(video_link, browser=chrome):
    browser.get(video_link)
    time.sleep(1)
    source_link = browser.find_element_by_tag_name(
        'video'
    ).find_element_by_tag_name('source').get_attribute('src')
    return source_link


courses_data = load_data('./DATA_DOWNLOADABLE.json')

def write_downloadable_data(courses_data):
    with open('DATA_DOWNLOADABLE.json', 'w') as file:
        file.write(json.dumps(courses_data))


def get_downloadable_links(courses_data):
    for course in courses_data:
        url = course['url']
        for section in course['sections']:
            for subsection in section['subsections']:

                if subsection['downloadable_url'] is None:
                    video_url = url + subsection['url']
                    print "Retriving: {0}/{1}/{2}".format(
                        format_filename(course['title']),
                        format_filename(section['title']),
                        format_filename(subsection['title']))
                    url_str = get_video_source(video_url)
                    print "Video URL: {0}".format(url_str)
                    subsection['downloadable_url'] = url_str
                    write_downloadable_data(courses_data)
                    time.sleep(3)

    return courses_data


# real_browser_login()
# get_downloadable_links(courses_data)

courses_detailed_data = load_data('./DATA_DOWNLOADABLE.json')

def create_path(path):
    if not os.path.exists(path):
        os.makedirs(path)


def download_courses(courses_array):
    # Create download directory
    create_path('./Download')

    for i0, course in enumerate(courses_array):
        title = course['title']
        # Create course directory
        course_path = './Download/{0}-{1}'.format(i0, title)
        create_path(course_path)

        for i1, section in enumerate(course['sections']):
            section_title = section['title']

            for i2, subsection in enumerate(section['subsections']):
                subsection_title = subsection['title']
                print "Downloading: {0}".format(
                    format_filename(subsection_title))

                filename = str(i1) + '-' + str(i2) + format_filename(
                    section_title) + '|' + format_filename(
                        subsection_title) + '.mp4'

                file_path = course_path + '/' + format_filename(filename)

                download_file(subsection['downloadable_url'], file_path)


download_courses(courses_detailed_data)
