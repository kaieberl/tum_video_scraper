import argparse
import logging
import os
import re
from time import sleep

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from typing import Dict, Tuple

import util


def login(tum_username: str, tum_password: str) -> webdriver:
    driver_options = webdriver.ChromeOptions()
    # driver_options.add_argument("--headless")
    if os.getenv('NO-SANDBOX') == '1':
        driver_options.add_argument("--no-sandbox")
    driver = webdriver.Chrome(options=driver_options)

    driver.get("https://live.rbg.tum.de/login")
    driver.find_element(By.XPATH, "/html/body/main/section/article/div/button").click()
    driver.find_element(By.ID, "username").send_keys(tum_username)
    driver.find_element(By.ID, "password").send_keys(tum_password)
    driver.find_element(By.ID, "username").submit()
    sleep(2)
    if "Couldn't log in. Please double check your credentials." in driver.page_source:
        driver.close()
        raise argparse.ArgumentTypeError("Username or password incorrect")
    return driver


def get_video_links_of_subject(driver: webdriver, subjects_identifier, camera_type) -> [(str, str)]:
    subject_url = "https://live.rbg.tum.de/old/course/" + subjects_identifier
    driver.get(subject_url)

    links_on_page = driver.find_elements(By.XPATH, ".//a")
    video_urls: [str] = []
    for link in links_on_page:
        link_url = link.get_attribute("href")
        if link_url and "https://live.rbg.tum.de/w/" in link_url:
            video_urls.append(link_url)

    video_urls = [url for url in video_urls if ("/CAM" not in url and "/PRES" not in url)]
    video_urls = list(dict.fromkeys(video_urls))  # deduplicate

    video_playlists: [(str, str)] = []
    for video_url in video_urls:
        driver.get(video_url + "/" + camera_type)
        sleep(2)
        try:
            filename = driver.find_element(By.XPATH, "//h1").text.strip()
        except NoSuchElementException:
            try:
                filename = driver.find_element(By.XPATH, "/html/body/div[2]/div/div[1]/video-js/video/source").text.strip()
            except NoSuchElementException:
                filename = driver.find_element(By.XPATH, "/html/body/div[3]/div/div[1]/video-js/video/source").text.strip()
        playlist_url = get_playlist_url(driver.page_source)
        logging.info(f'Found video "{filename}" at {playlist_url}')
        video_playlists.append((filename, playlist_url))

    video_playlists.reverse()
    return video_playlists


def get_playlist_url(source: str) -> str:
    playlist_extracted_match = re.search(r"(https://\S+?/playlist\.m3u8.*?)[\'|\"]", source)
    if not playlist_extracted_match:
        raise Exception("Could not extract playlist URL from TUM-live! Page source:\n" + source)
    playlist_url = playlist_extracted_match.group(1)
    return playlist_url


def get_subjects(subjects: Dict[str, Tuple[str, str]], tum_username: str, tum_password: str, queue: [str, Tuple[str, str]]):
    driver = login(tum_username, tum_password)
    for subject_name, (subjects_identifier, camera_type) in subjects.items():
        m3u8_playlists = get_video_links_of_subject(driver, subjects_identifier, camera_type)
        # m3u8_playlists = util.enumerate_list(m3u8_playlists)  # enumerate_list not found
        print(f'Found {len(m3u8_playlists)} videos for "{subject_name}"')
        queue.append((subject_name, m3u8_playlists))
    driver.close()
