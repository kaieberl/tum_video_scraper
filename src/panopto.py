import argparse
import re
from pathlib import Path
from time import sleep

from selenium import webdriver

import downloader


def get_video_links_in_folder(driver: webdriver, folder_id: str) -> [(str, str)]:
    folder_link = f"https://tum.cloud.panopto.eu/Panopto/Pages/Sessions/List.aspx#folderID=%22" \
                  f"{folder_id}" \
                  f"%22&maxResults=250"
    driver.get(folder_link)
    sleep(3)
    if "Failed to load folder" in driver.title:
        print("Folder-ID incorrect: " + folder_id)
        raise Exception

    links_on_page = driver.find_elements_by_xpath(".//a")
    video_urls: [str] = []
    for link in links_on_page:
        link_url = link.get_attribute("href")
        if link_url and "https://tum.cloud.panopto.eu/Panopto/Pages/Viewer.aspx" in link_url:
            video_urls.append(link_url)

    video_playlists: [(str, str)] = []
    for video_url in video_urls:
        video_id = video_url[-36:]
        video_playlists.append(get_m3u8_playlist(driver, video_id))

    video_playlists = util.dedup(video_playlists)
    video_playlists.reverse()

    return video_playlists


def get_m3u8_playlist(driver: webdriver, video_id: str) -> (str, str):
    video_url = "https://tum.cloud.panopto.eu/Panopto/Pages/Embed.aspx?id=" + video_id
    sleep(1)    # else server blocks crawler
    driver.get(video_url)

    prefix = "\"VideoUrl\":\""
    postfix = "/master.m3u8"
    matches = re.search(prefix + '(.+?)' + postfix, driver.page_source)
    if not matches:
        print("Error on URL " + video_url + " - " + driver.title)
        return
    playlist_extracted_url = matches.group(1)
    playlist_url = playlist_extracted_url.replace('\\', '') + postfix
    filename = driver.title.strip()
    return filename, playlist_url


def get_folders(panopto_folders: dict[str, str], tum_username: str, tum_password: str, queue: [str, (str, str)]):
    driver = login(tum_username, tum_password)
    for subject_name, folder_id in panopto_folders.items():
        m3u8_playlists = get_video_links_in_folder(driver, folder_id)
        m3u8_playlists = util.rename_duplicates(m3u8_playlists)
        print(f'Found {len(m3u8_playlists)} videos for "{subject_name}"')
        queue.append((subject_name, m3u8_playlists))
    driver.close()
