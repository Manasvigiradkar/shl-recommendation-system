"""
SHL Product Catalog Scraper using Selenium
Handles JavaScript-rendered content and dynamic loading
"""
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import json
import time
from typing import List, Dict
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SHLSeleniumScraper:
    def __init__(self, headless: bool = True):
        self.base_url = "https://www.shl.com"
        self.catalog_url = "https://www.shl.com/solutions/products/product-catalog/"
        self.assessments = []
        self.headless = headless
        self.driver = None
        
    def setup_driver(self):
        """Setup Chrome driver with options."""
        chrome_options = Options()
        
        if self.headless:
            chrome_options.add_argument('--headless')
        
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.maximize_window()
        logger.info("✓ Chrome driver initialized")
    
    def scrape_catalog(self) -> List[Dict]:
        """Main scraping method using Selenium."""
        try:
            self.setup_driver()
            logger.info(f"🌐 Loading catalog page: {self.catalog_url}")
            
            self.driver.get(self.catalog_url)
            
            # Wait for page to load
            time.sleep(5)
            
            # Scroll to load all content (if lazy-loaded)
            self._scroll_page()
            
            # Extract assessment links
            assessment_links = self._extract_assessment_links()
            logger.info(f"Found {len(assessment_links)} assessment links")
            
            # Scrape each assessment
            for idx, link in enumerate(assessment_links, 1):
                logger.info(f"Scraping {idx}/{len(assessment_links)}: {link}")
                assessment_data = self._scrape_assessment_page(link)
                if assessment_data:
                    self.assessments.append(assessment_data)
                time.sleep(2)
            
            logger.info(f"✅ Successfully scraped {len(self.assessments)} assessments")
            
            if self.assessments:
                self._save_to_file()
            
            return self.assessments
            
        except Exception as e:
            logger.error(f"Error during scraping: {e}", exc_info=True)
            return []
        finally:
            if self.driver:
                self.driver.quit()
                logger.info("Browser closed")
    
    def _scroll_page(self):
        """Scroll page to trigger lazy loading."""
        logger.info("Scrolling page to load all content...")
        
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        
        for _ in range(5):  # Scroll 5 times
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height
    
    def _extract_assessment_links(self) -> List[str]:
        """Extract assessment links from the catalog page."""
        links = set()
        
        # Try multiple CSS selectors
        selectors = [
            "a[href*='/product/']",
            "a[href*='/assessment/']",
            "a[href*='/test/']",
            "a[href*='verify']",
            "a[href*='reasoning']",
            "div.product-card a",
            "div.assessment-card a",
            "article a",
            ".card a",
            ".product a"
        ]
        
        for selector in selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                logger.info(f"Selector '{selector}' found {len(elements)} elements")
                
                for element in elements:
                    try:
                        href = element.get_attribute('href')
                        if href and self._is_valid_assessment_link(href):
                            links.add(href)
                    except:
                        continue
            except Exception as e:
                logger.debug(f"Selector '{selector}' failed: {e}")
        
        # If no links found, try JavaScript extraction
        if len(links) == 0:
            logger.info("Trying JavaScript extraction...")
            js_links = self.driver.execute_script("""
                return Array.from(document.querySelectorAll('a'))
                    .map(a => a.href)
                    .filter(href => href.includes('product') || 
                                   href.includes('assessment') || 
                                   href.includes('test') ||
                                   href.includes('verify') ||
                                   href.includes('reasoning'));
            """)
            links.update([link for link in js_links if self._is_valid_assessment_link(link)])
        
        return sorted(list(links))
    
    def _is_valid_assessment_link(self, url: str) -> bool:
        """Check if URL is a valid assessment link."""
        exclude = ['pre-packaged', 'job-solution', 'blog', 'news', 'contact', 
                  'about', 'privacy', 'terms', 'login', '.pdf', '.jpg', '#']
        
        url_lower = url.lower()
        
        if any(pattern in url_lower for pattern in exclude):
            return False
        
        include = ['/product/', '/assessment/', '/test/', 'verify', 'reasoning', 
                  'personality', 'cognitive', 'aptitude', 'opq']
        
        return self.base_url in url and any(pattern in url_lower for pattern in include)
    
    def _scrape_assessment_page(self, url: str) -> Dict:
        """Scrape individual assessment page."""
        try:
            self.driver.get(url)
            
            # Wait for page to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "h1"))
            )
            
            time.sleep(2)
            
            # Extract data
            name = self._get_element_text(By.TAG_NAME, "h1", "Unknown Assessment")
            
            description = self._extract_description_selenium()
            
            page_text = self.driver.find_element(By.TAG_NAME, "body").text.lower()
            
            test_type = self._determine_test_type(page_text, description)
            
            metadata = {
                'name': name.split('|')[0].strip(),
                'url': url,
                'description': description,
                'test_type': test_type,
                'category': self._extract_category_selenium(),
                'duration': self._extract_duration_selenium(page_text),
                'level': self._determine_level(page_text),
                'skills': self._extract_skills_selenium(page_text),
                'format': 'Online' if 'online' in page_text or 'digital' in page_text else 'Standard'
            }
            
            logger.info(f"✓ Extracted: {metadata['name']}")
            return metadata
            
        except Exception as e:
            logger.error(f"Error scraping {url}: {e}")
            return None
    
    def _get_element_text(self, by, value, default=""):
        """Safely get text from element."""
        try:
            element = self.driver.find_element(by, value)
            return element.text.strip()
        except:
            return default
    
    def _extract_description_selenium(self) -> str:
        """Extract description using Selenium."""
        selectors = [
            (By.CSS_SELECTOR, "meta[name='description']"),
            (By.CSS_SELECTOR, "meta[property='og:description']"),
            (By.CSS_SELECTOR, ".description"),
            (By.CSS_SELECTOR, ".summary"),
            (By.CSS_SELECTOR, ".intro"),
            (By.TAG_NAME, "p")
        ]
        
        for by, value in selectors:
            try:
                element = self.driver.find_element(by, value)
                if by == By.CSS_SELECTOR and 'meta' in value:
                    text = element.get_attribute('content')
                else:
                    text = element.text
                
                if text and len(text) > 50:
                    return text[:500]
            except:
                continue
        
        return ""
    
    def _extract_category_selenium(self) -> str:
        """Extract category using Selenium."""
        selectors = [
            ".category",
            ".tag",
            ".badge",
            ".label",
            "nav.breadcrumb a"
        ]
        
        for selector in selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for elem in elements:
                    text = elem.text.strip()
                    if text and 3 < len(text) < 50:
                        return text
            except:
                continue
        
        return "General"
    
    def _extract_duration_selenium(self, page_text: str) -> str:
        """Extract duration from page text."""
        import re
        patterns = [
            r'(\d+(?:\.\d+)?)\s*(?:hour|hr)s?',
            r'(\d+)\s*(?:minute|min)s?'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, page_text, re.I)
            if match:
                return match.group(0).strip()
        
        return "N/A"
    
    def _determine_test_type(self, text: str, description: str) -> str:
        """Determine test type from text."""
        combined = (text + ' ' + description).lower()
        
        if any(w in combined for w in ['personality', 'behavior', 'opq', 'trait']):
            return "P"
        elif any(w in combined for w in ['cognitive', 'ability', 'reasoning', 'numerical', 'verbal']):
            return "C"
        elif any(w in combined for w in ['knowledge', 'skill', 'technical', 'coding']):
            return "K"
        elif any(w in combined for w in ['situational', 'judgment', 'sjt']):
            return "S"
        
        return "O"
    
    def _determine_level(self, text: str) -> str:
        """Determine job level from text."""
        if any(w in text for w in ['senior', 'executive', 'leadership']):
            return "Senior"
        elif any(w in text for w in ['mid-level', 'intermediate', 'experienced']):
            return "Mid-Level"
        elif any(w in text for w in ['entry', 'junior', 'graduate']):
            return "Entry-Level"
        return "All Levels"
    
    def _extract_skills_selenium(self, text: str) -> List[str]:
        """Extract skills from text."""
        skills = ['leadership', 'communication', 'teamwork', 'problem-solving',
                 'analytical', 'critical thinking', 'numerical', 'verbal',
                 'logical', 'attention to detail', 'planning']
        
        found = [skill for skill in skills if skill in text]
        return found[:5]
    
    def _save_to_file(self, filename: str = 'data/shl_assessments.json'):
        """Save data to JSON file."""
        import os
        os.makedirs('data', exist_ok=True)
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.assessments, f, indent=2, ensure_ascii=False)
        logger.info(f"💾 Saved {len(self.assessments)} assessments to {filename}")


def main():
    print("\n" + "="*70)
    print("SHL SELENIUM SCRAPER")
    print("="*70 + "\n")
    
    print("📋 REQUIREMENTS:")
    print("  - Chrome browser installed")
    print("  - ChromeDriver installed (pip install webdriver-manager)")
    print("  - selenium package (pip install selenium)")
    print("\n")
    
    scraper = SHLSeleniumScraper(headless=False)  # Set to True for headless
    assessments = scraper.scrape_catalog()
    
    print(f"\n{'='*70}")
    print(f"SCRAPING COMPLETE!")
    print(f"Total assessments: {len(assessments)}")
    print(f"{'='*70}\n")
    
    if assessments:
        print("📊 SAMPLE ASSESSMENTS:")
        for i, a in enumerate(assessments[:5], 1):
            print(f"\n{i}. {a['name']}")
            print(f"   Type: {a['test_type']}")
            print(f"   Category: {a['category']}")

if __name__ == "__main__":
    main()