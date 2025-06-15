#!/usr/bin/env python3
import os
import time
import random
import argparse
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import (
    TimeoutException,
    ElementClickInterceptedException,
    ElementNotInteractableException
)
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# CONFIG
LANDID_USERNAME          = os.getenv("LANDID_USERNAME", "aaron@fulleroak.com")
LANDID_PASSWORD          = os.getenv("LANDID_PASSWORD", "cU2Vj1GNGEklgdSN")
SIGNIN_URL               = "https://id.land/users/sign_in"
CREATE_MAP_BTN_XPATH     = '//*[@id="app"]/div/main/div[1]/header/div/div[3]/div[2]/button[1]'
TITLE_INPUT_XPATH        = "//h1[normalize-space()='Create New Map']/following::input[1]"
PARCEL_SEARCH_XPATH      = "//button[normalize-space()='GO']"
BOUNDARY_BTN_XPATH       = '//*[@id="panels"]/div/div/div/div/div[2]/div[2]/div[1]/div[1]/div/div[2]/div[1]/div/button[1]/span'
CONFIRM_SAVE_BOUNDARY    = '/html/body/div[8]/div/div/main/div[2]/div[4]/button[1]'
# END CONFIG

def human_sleep(base=1.0, variance=0.5):
    """Sleep a bit to mimic human timing."""
    time.sleep(max(0.2, base + random.uniform(-variance, variance)))


def login(driver):
    driver.get(SIGNIN_URL)
    human_sleep(2,1)
    WebDriverWait(driver,20).until(
        EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Email address']"))
    )
    driver.find_element(By.XPATH, "//input[@placeholder='Email address']").send_keys(LANDID_USERNAME)
    human_sleep(1,0.3)
    driver.find_element(By.XPATH, "//input[@placeholder='Password']").send_keys(LANDID_PASSWORD)
    human_sleep(1,0.3)
    WebDriverWait(driver,10).until(
        EC.element_to_be_clickable((By.XPATH, "//button[normalize-space()='Sign In']"))
    ).click()
    WebDriverWait(driver,20).until(
        EC.element_to_be_clickable((By.XPATH, CREATE_MAP_BTN_XPATH))
    )
    human_sleep()


def select_parcel_search_mode(driver):
    """
    Switch search to Parcel ID mode.
    """
    toggle = WebDriverWait(driver,15).until(
        EC.element_to_be_clickable((By.XPATH,
            "//div[contains(@class,'top-select-control')][.//p[normalize-space()='Smart Search']]"
        ))
    )
    human_sleep(0.3)
    try:
        toggle.click()
    except (ElementClickInterceptedException, ElementNotInteractableException):
        driver.execute_script("arguments[0].click()", toggle)
    human_sleep(1)

    for xpath in [
        "//ul[contains(@class,'top-select-control__items')]//p[normalize-space()='Parcel']",
        "//ul[contains(@class,'top-select-control__sub_items')]//p[normalize-space()='Parcel ID']"
    ]:
        opt = WebDriverWait(driver,10).until(
            EC.element_to_be_clickable((By.XPATH, xpath))
        )
        human_sleep(0.2)
        try:
            opt.click()
        except (ElementClickInterceptedException, ElementNotInteractableException):
            driver.execute_script("arguments[0].click()", opt)
        human_sleep(0.8)

    WebDriverWait(driver,10).until(
        EC.presence_of_all_elements_located((By.CSS_SELECTOR, "#top-bar input"))
    )
    human_sleep()


def create_map_for_parcel(driver, title, state_code):
    WebDriverWait(driver,15).until(
        EC.element_to_be_clickable((By.XPATH, CREATE_MAP_BTN_XPATH))
    ).click()
    human_sleep(1.5,0.5)

    title_in = WebDriverWait(driver,10).until(
        EC.presence_of_element_located((By.XPATH, TITLE_INPUT_XPATH))
    )
    title_in.clear()
    human_sleep(0.3)
    title_in.send_keys(title)
    human_sleep(0.8)

    gid = f"state-group-{state_code.lower()}"
    WebDriverWait(driver,10).until(
        EC.element_to_be_clickable((By.ID, gid))
    ).click()
    human_sleep(1)

    WebDriverWait(driver,10).until(
        EC.element_to_be_clickable((By.XPATH, "//button[normalize-space()='Start Mapping']"))
    ).click()
    human_sleep(2)


def process_parcel(driver, apn, county):
    """
    Search for the parcel by county & APN, then save its boundary and return the new map URL.
    """
    select_parcel_search_mode(driver)

    # Enter county
    county_in = None
    try:
        county_in = driver.find_element(By.CSS_SELECTOR, 'input[placeholder="County"]')
    except:
        county_in = driver.find_elements(By.CSS_SELECTOR, "#top-bar input")[0]
    county_in.clear(); human_sleep(0.3)
    county_in.send_keys(county);   human_sleep(0.5)

    try:
        li = WebDriverWait(driver,5).until(
            EC.element_to_be_clickable((By.XPATH,
                '//*[@id="react-autowhatever-countyAutosuggest"]//li[1]'
            ))
        )
        li.click()
    except TimeoutException:
        pass
    human_sleep()

    # Enter APN
    id_in = None
    try:
        id_in = driver.find_element(By.CSS_SELECTOR, 'input[placeholder="ID"]')
    except:
        id_in = driver.find_elements(By.CSS_SELECTOR, "#top-bar input")[1]
    id_in.clear(); human_sleep(0.3)
    id_in.send_keys(apn);       human_sleep(0.5)

    # GO
    go_btn = WebDriverWait(driver,10).until(
        EC.element_to_be_clickable((By.XPATH, PARCEL_SEARCH_XPATH))
    )
    try:
        go_btn.click()
    except:
        driver.execute_script("arguments[0].click()", go_btn)

    # Wait for boundary button
    WebDriverWait(driver,20).until(
        EC.element_to_be_clickable((By.XPATH, BOUNDARY_BTN_XPATH))
    )
    human_sleep(1)

    # Save boundary
    boundary_btn = driver.find_element(By.XPATH, BOUNDARY_BTN_XPATH)
    boundary_btn.click(); human_sleep(0.5)

    # Confirm save
    confirm = WebDriverWait(driver,10).until(
        EC.element_to_be_clickable((By.XPATH, CONFIRM_SAVE_BOUNDARY))
    )
    confirm.click(); human_sleep(1)

    return driver.current_url


def main(input_path, output_path):
    # Load input
    if input_path.lower().endswith('.csv'):
        df = pd.read_csv(input_path, dtype=str)
    else:
        df = pd.read_excel(input_path, dtype=str, engine="openpyxl")
    df.columns = df.columns.str.strip()

    if "Land.id Link" not in df.columns:
        df["Land.id Link"] = ""

    # Process all records
    total = len(df)
    for idx in range(total):
        row = df.loc[idx]
        apn    = str(row.get("APN", "")).strip()
        county = str(row.get("County Name", "")).strip()
        state  = str(row.get("State", "")).strip()
        owner  = str(row.get("Owner Mailing Name", "")).strip()
        ref    = str(row.get("Reference", "")).strip()
        title  = "{} - {}".format(ref, owner)
        print("[{}/{}] Starting browser for APN={}, County={}".format(idx+1, total, apn, county))

        # Launch and login with cloud-friendly options
        opts = Options()
        opts.add_argument("--headless")  # Run in headless mode for cloud
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
        opts.add_argument("--disable-gpu")
        opts.add_argument("--disable-extensions")
        opts.add_argument("--disable-background-timer-throttling")
        opts.add_argument("--disable-backgrounding-occluded-windows")
        opts.add_argument("--disable-renderer-backgrounding")
        opts.add_argument("--disable-features=TranslateUI")
        opts.add_argument("--disable-ipc-flooding-protection")
        opts.add_argument("--window-size=1920,1080")
        opts.add_argument("--remote-debugging-port=9222")
        opts.add_argument("--user-data-dir=/tmp/chrome-user-data")
        opts.add_argument("--single-process")
        
        try:
            from webdriver_manager.chrome import ChromeDriverManager
            from selenium.webdriver.chrome.service import Service
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=opts)
        except:
            # Fallback for local development
            driver = webdriver.Chrome(options=opts)
        try:
            login(driver)
            create_map_for_parcel(driver, title, state)
            map_url = process_parcel(driver, apn, county)
            df.at[idx, "Land.id Link"] = map_url
            print("[{}/{}] Saved URL: {}".format(idx+1, total, map_url))
        finally:
            driver.quit()
            human_sleep(1)

    # Save results
    if output_path.lower().endswith('.csv'):
        df.to_csv(output_path, index=False)
    else:
        df.to_excel(output_path, index=False, engine="openpyxl")
    print("\nProcessing complete. {} entries updated in: {}".format(total, output_path))

if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Automate ID.land boundary save per parcel")
    p.add_argument("--input",  required=True, help="Path to input .csv or .xlsx file")
    p.add_argument("--output", required=True, help="Path to output .csv or .xlsx file")
    args = p.parse_args()
    main(args.input, args.output)