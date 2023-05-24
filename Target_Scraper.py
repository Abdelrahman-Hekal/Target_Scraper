from selenium import webdriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait as wait
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
import pandas as pd
import time
import unidecode
import csv
import sys
import numpy as np

def initialize_bot():

    # Setting up chrome driver for the bot
    chrome_options  = webdriver.ChromeOptions()
    # suppressing output messages from the driver
    chrome_options.add_argument('--log-level=3')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--disable-extensions')
    chrome_options.add_argument('--window-size=1920,1080')
    # adding user agents
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36")
    chrome_options.add_argument("--incognito")
    chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
    # running the driver with no browser window
    #chrome_options.add_argument('--headless')
    # disabling images rendering 
    prefs = {"profile.managed_default_content_settings.images": 2}
    chrome_options.add_experimental_option("prefs", prefs)
    # installing the chrome driver
    driver_path = ChromeDriverManager().install()
    # configuring the driver
    driver = webdriver.Chrome(driver_path, options=chrome_options)
    driver.set_page_load_timeout(60)
    driver.maximize_window()

    return driver

def scrape_target(path):

    start = time.time()
    print('-'*75)
    print('Scraping target.com ...')
    print('-'*75)
    # initialize the web driver
    driver = initialize_bot()

    # initializing the dataframe
    data = pd.DataFrame()

    # if no books links provided then get the links
    if path == '':
        name = 'target_data.csv'
        # getting the books under each category
        driver.get('https://www.target.com/c/books-movies-music/-/N-5xsxd')
        time.sleep(3)
        links = []

        for _ in range(3):
            try:
                # clicking on show all buttons
                buttons = wait(driver, 5).until(EC.presence_of_all_elements_located((By.TAG_NAME, "button")))
                for button in buttons:
                    if 'show more' in button.get_attribute('textContent').lower():
                        driver.execute_script("arguments[0].click();", button)
                        time.sleep(1)
                # getting the list of books categories
                categories = {}
                lis = wait(driver, 5).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "li.styles__StyledLi-sc-2nwvzd-1.fIlnsp")))
                ncats = len(lis)
                for i, li in enumerate(lis):
                    a = wait(li, 5).until(EC.presence_of_element_located((By.TAG_NAME, "a")))
                    cat = a.get_attribute("textContent")
                    link = a.get_attribute("href")
                    categories[cat] = link

                # scraping books under each category
                for j, cat in enumerate(categories.keys()):
                    print("-"*75)
                    print(f'Scraping books urls under Category: {cat} {j+1}/{ncats}')
                    link = categories[cat]
                    driver.get(link)
                    n = 0
                    try:
                        span = wait(driver, 5).until(EC.presence_of_element_located((By.CSS_SELECTOR, "span.Pagination__StyledSpan-sc-sq3l8r-5.bpskxx")))
                        npages = int(span.text.split(' ')[-1])
                    except:
                        npages = 1
                    
                    for j in range(1, npages):
                        try:
                            section = wait(driver, 5).until(EC.presence_of_element_located((By.CSS_SELECTOR, "section.styles__StyledRowWrapper-sc-z8946b-1.jvgxLX")))
                            divs = wait(section, 5).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.styles__StyledCol-sc-fw90uk-0.fPNzT")))
                            for div in divs:
                                print(f"Getting the link for book {n+1}")
                                a = wait(div, 5).until(EC.presence_of_all_elements_located((By.TAG_NAME, "a")))[0]
                                url = a.get_attribute("href")
                                links.append((url, cat))

                                n += 1
                            # moving to the next page
                            button = wait(driver, 2).until(EC.presence_of_element_located((By.XPATH, "//button[@type='button' and @aria-label='next page']")))
                            driver.execute_script("arguments[0].click();", button)
                            print(f"Moving to page {j+1}/{npages}")
                            time.sleep(5)
                        except:
                            pass

                # saving the links to a csv file
                print('Exporting links to a csv file ....')
                with open('target_links.csv', 'w', newline='\n', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(['Link', 'Category'])
                    for row in links:
                        writer.writerow([row[0], row[1]])

                break
            except Exception as err:
                print('The below error occurred during the scraping from target.com, retrying ..')
                print('-'*50)
                print(err)
                print('-'*50)
                driver.quit()
                time.sleep(10)
                driver = initialize_bot()

    scraped = []
    if path != '':
        df_links = pd.read_csv(path)
    else:
        df_links = pd.read_csv('target_links.csv')

    links = df_links['Link'].values.tolist()
    cats = df_links["Category"].values.tolist()
    name = path.split('\\')[-1][:-4]
    name = name + '_data.csv'
    try:
        data = pd.read_csv(name)
        scraped = data['Title Link'].values.tolist()
    except:
        pass
    # scraping books details
    print('-'*75)
    print('Scraping Books Info...')
    print('-'*75)
    n = len(links)
    for i, link in enumerate(links):
        cat = cats[i]
        try:
            if link in scraped: continue
            driver.get(link)
            details = {}
            details['Category'] = cat
            print(f'Scraping the info for book {i+1}\{n}')
            score, nrev = '', ''
            try:
                rating = wait(driver, 5).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "span.utils__ScreenReaderOnly-sc-1b93ups-0.TZdMr")))[0].text
                score = float(rating.split(' ')[0])
                nrev = int(rating.split(' ')[-2])
            except:
                pass

            price = ''
            try:
                price = wait(driver, 5).until(EC.presence_of_element_located((By.CSS_SELECTOR, "span[data-test='product-price']"))).text.replace('$', '')
            except:
                pass

            details['Rating'] = score
            details['Number of Reviews'] = nrev
            details['Price'] = price
            #print(score, nrev, price)
            # title and title link
            title_link, title = '', ''
            try:
                title_link = link
                title = wait(driver, 2).until(EC.presence_of_element_located((By.XPATH, "//h1[@data-test='product-title']"))).text.title() 
                title = unidecode.unidecode(title)
            except:
                print(f'Warning: failed to scrape the title for book: {link}')            
                
            details['Title'] = title
            details['Title Link'] = title_link
            # clicking on "Show more" buttons
            buttons = wait(driver, 2).until(EC.presence_of_all_elements_located((By.TAG_NAME, "button")))
            for button in buttons:
                if 'Show more' in button.text:
                    driver.execute_script("arguments[0].click();", button)
                    time.sleep(1)

            # other info
            author = ''
            cols = ["Author:", 'Suggested Age:', 'Number of Pages:', 'Format:', 'Genre:', 'Publisher:', 'Language:', 'Street Date: ', 'TCIN:', 'UPC:', 'Item Number (DPCI):', 'Origin:']            
            try:
                info = wait(driver, 2).until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.styles__StyledCol-sc-fw90uk-0.dFHUpo.h-padding-h-tight")))
                divs = wait(info, 2).until(EC.presence_of_all_elements_located((By.TAG_NAME, "div")))
                for div in divs:
                    for col in cols:
                        if col in div.get_attribute("textContent"):
                            text = div.get_attribute("textContent").split(col)[-1].strip()
                            try:
                                text = int(text)
                            except:
                                text = unidecode.unidecode(text)
                            details[col.replace(':', "")] = text
            except:
                pass            
                                   
            # appending the output to the datafame            
            data = data.append([details.copy()])
            # saving data to csv file each 100 links
            if np.mod(i+1, 100) == 0:
                print('Outputting scraped data to csv file ...')
                data.to_csv(name, encoding='UTF-8', index=False)
        except:
            pass

    # optional output to csv
    data.to_csv(name, encoding='UTF-8', index=False)
    elapsed = round((time.time() - start)/60, 2)
    print('-'*75)
    print(f'target.com scraping process completed successfully! Elapsed time {elapsed} mins')
    print('-'*75)
    driver.quit()

    return data

if __name__ == "__main__":
    
    path = ''
    if len(sys.argv) == 2:
        path = sys.argv[1]
    data = scrape_target(path)

