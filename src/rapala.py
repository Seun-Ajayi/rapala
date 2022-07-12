from webbrowser import Chrome
from bs4 import BeautifulSoup as bs
from selenium import webdriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.firefox.options import Options as Firefox_Options
from selenium.webdriver.chrome.options import Options as Chrome_Options
from selenium.webdriver.firefox.service import Service as Firefox_Service
from selenium.webdriver.chrome.service import Service as Chrome_Service
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.by import By
import argparse
import time
import yaml
from typing import Any, Dict, List

CONFIG = yaml.load(open("config.yml"), Loader=yaml.FullLoader)

def get_parser() -> argparse.ArgumentParser:
    """
    parse command line arguments

    returns:
        parser - ArgumentParser object
    """

    parser = argparse.ArgumentParser(description='VOA NEWS Scraper')
    parser.add_argument(
        '--driver_type',
        type=str.lower,
        default= 'chrome_driver',
        choices= ['firefox_driver', 'chrome_driver'],
        help='driver_type: firefox_driver or chrome_driver, default: chrome_driver'
)
    parser.add_argument(
        '--driver_path',
        type=str,
        help='Path of the driver of choice e.g: "C:\Program Files\chromedriver.exe"'
)
    parser.add_argument(
        '--filename',
        type=str,
        help='Name of the output file'
)
    parser.add_argument(
        '--source_to_start_from',
        type=int,
        default=0,
        help='Source to start scraping from, default: 0'
)
    parser.add_argument(
        '--page_to_start_from',
        type=int,
        default=0,
        help='Page to start scraping from, default: 0'
)
    parser.add_argument(
        '--article_to_start_from',
        type=int,
        default=0,
        help='Article to start scraping from, default: 0'
)


    return parser 


class Rapala:
    def __init__(
        self,
        driver_path: str = None,
        driver_type: str = None,
        prefs: Dict[str, Any] = None,
        filename: str = None,
        unallowed_tokens: List = None,
        source_to_start_from: int = None,
        page_to_start_from: int = None,
        article_to_start_from: int = None,
    ) -> None:
        """ """
        self.page_to_start_from = page_to_start_from 
        self.article_to_start_from = article_to_start_from 
        self.source_to_start_from = source_to_start_from 

        self.driver_path = driver_path 
        self.driver_type = driver_type

        # disable images in browser for faster loading.
        self.prefs = prefs or {"profile.managed_default_content_settings.images": 2}
        self.driver = None

        self.first_article_path = CONFIG['FIRST_ARTICLE_PATH1'] or CONFIG['FIRST_ARTICLE_PATH2'] 
        self.article_path = CONFIG['ARTICLE_PATH1'] or CONFIG['ARTICLE_PATH2'] or CONFIG['ART']
        self.sources = CONFIG['SOURCES']

        self.sources_page_limit =  CONFIG['PAGE_LIMIT']

        self.unallowed_tokens = unallowed_tokens or [
            "Print",
            "No media source currently available",
        ]
        self.filename = filename or "voa_swahili_{}_{}_{}_{}.txt".format(
            time.strftime("%Y%m%d-%H%M%S"),
            self.source_to_start_from,
            self.page_to_start_from,
            self.article_to_start_from,
        )
        self.file = open(self.filename, "w+", encoding="utf-8")

    def init_driver(self) -> webdriver:
        """
        This func initializes the webdriver and disables images
        A wait is initialized with a 5 second timeout
        """
       
        firefox_options = Firefox_Options()
        chrome_options = Chrome_Options()

        driver_dict = {"firefox_driver": webdriver.Firefox, "chrome_driver": webdriver.Chrome}
        option_dict = {"firefox_driver": firefox_options, "chrome_driver": chrome_options}
        service_dict = {"firefox_driver": Firefox_Service, "chrome_driver": Chrome_Service}

        # option_dict[self.driver_type].add_argument("--headless")
        option_dict[self.driver_type].add_experimental_option("prefs", self.prefs)
        service = service_dict[self.driver_type](self.driver_path)
        driver = driver_dict[self.driver_type](service=service, options=option_dict[self.driver_type])

        # define a generic wait to be used throughout
        driver.wait = WebDriverWait(driver, 5)

        return driver

    def __write_article_to_text(self, sentences: str) -> None:
        """
        This func writes individual sentences to the file
        """
        sentence_split = filter(None, sentences.split("."))
        for s in sentence_split:
            self.file.write(s.strip() + "\n")

    def __on_article_action(self) -> None:
        """
        This func contains all actions that happen when an article is opened
        """
        
        content = self.driver.page_source
        soup = bs(content, "html.parser")
     
        title = soup.find(
            "h1", attrs={"class": CONFIG['TITLE_CLASS']}
        )
        if title == None:
            title = soup.find(
                "div", attrs={"class": CONFIG['TITLE_CLASS2']}
            )
        self.__write_article_to_text(title.text.strip())

        category = soup.find(
            "div", attrs={"class": CONFIG['CATEGORY_CLASS']}
        ).text.strip()
        self.__write_article_to_text(category)
        # loop over individual p-elements
        # & write their text to file
        for line in soup.findAll("p"):
            # remove unallowed tokens from text written to file
            if line.text.strip() not in self.unallowed_tokens:
                self.__write_article_to_text(line.text)

    def open_article_and_collect(self, article_path: str) -> None:
        """
        This func open an article on the same browser window,
        calls on_article_action and then returns to the index
        page.
        """

        # get link of article to be collected
        WebElement
        button = WebDriverWait(self.driver, 15).until(
            EC.visibility_of_element_located((By.XPATH, article_path))
        )
        button.click()
    
        self.__on_article_action()
        self.driver.back()
        time.sleep(1)

    def start(self):
        """
        This func uses all previous functions to
        loop over all the sources and collect all articles
        into a file.
        """

        # initialize the driver
        self.driver = self.init_driver()

        try:
            for i in range(self.source_to_start_from, len(self.sources)):
                print("Collecting source: {}".format(self.sources[i]))

                # loop over the number of pages that section has, starting from pages_collected
                for j in range(self.page_to_start_from, self.sources_page_limit[i]):

                    self.driver.get(self.sources[i].format(j))
                    # loop over the number of articles on the page
                    for k in range(self.article_to_start_from, 12):
                        if k == 0:
                            # collect the first article on the page
                            self.open_article_and_collect(self.first_article_path)
                            continue
                        elif k > 2:
                            self.driver.execute_script(
                                "arguments[0].scrollIntoView();",
                                self.driver.find_element(
                                    By.XPATH, self.article_path.format(k - 2)
                                ),
                            )
                            time.sleep(1)
                        self.open_article_and_collect(self.article_path.format(k))
            self.file.close()
            self.driver.close()
            print(
                "O ti pari! The end l'opin cinema. I love you lo n gbeyin mills and boon."
            )
        except Exception as e:
            self.file.close()
            self.driver.close()
            print("Failed after: Source {} Page {} Article {}".format(i, j, k))
            raise e


if __name__ == "__main__":

    parser = get_parser()
    params, _ = parser.parse_known_args()
    
    rpl = Rapala(
        driver_path= params.driver_path, 
        driver_type= params.driver_type,
        filename= params.filename,
        source_to_start_from= params.source_to_start_from,
        page_to_start_from= params.page_to_start_from,
        article_to_start_from= params.article_to_start_from
    )
    rpl.start()
