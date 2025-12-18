"""
SHL Product Catalog Web Scraper - Enhanced Version
Handles multiple scraping strategies and respects robots.txt
"""
import requests
from bs4 import BeautifulSoup
import json
import time
from typing import List, Dict, Optional
import re
from urllib.robotparser import RobotFileParser
from urllib.parse import urljoin, urlparse
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SHLScraper:
    def __init__(self):
        self.base_url = "https://www.shl.com"
        self.catalog_url = "https://www.shl.com/solutions/products/product-catalog/"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        self.assessments = []
        self.robot_parser = None
        
    def check_robots_txt(self) -> bool:
        """Check if scraping is allowed by robots.txt."""
        try:
            self.robot_parser = RobotFileParser()
            self.robot_parser.set_url(f"{self.base_url}/robots.txt")
            self.robot_parser.read()
            
            can_fetch = self.robot_parser.can_fetch("*", self.catalog_url)
            logger.info(f"Robots.txt check: {'Allowed' if can_fetch else 'Disallowed'}")
            return can_fetch
        except Exception as e:
            logger.warning(f"Could not check robots.txt: {e}")
            return False
    
    def scrape_catalog(self, respect_robots: bool = True) -> List[Dict]:
        """Main scraping method to get all Individual Test Solutions."""
        logger.info("Starting SHL catalog scrape...")
        
        # Check robots.txt
        if respect_robots and not self.check_robots_txt():
            logger.error("❌ Scraping is disallowed by robots.txt")
            logger.info("\n⚠️  ALTERNATIVE APPROACHES:")
            logger.info("1. Manual Data Entry: Use browser to copy assessment data")
            logger.info("2. Official API: Check if SHL provides an official API")
            logger.info("3. Contact SHL: Request official data access")
            logger.info("4. Selenium with human-like behavior: Use headless browser")
            logger.info("5. Use publicly available SHL documentation/brochures")
            return []
        
        try:
            # Fetch the main catalog page with retry logic
            response = self._fetch_with_retry(self.catalog_url)
            if not response:
                return []
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Try multiple methods to extract assessment links
            assessment_links = self._extract_assessment_links_comprehensive(soup)
            
            logger.info(f"Found {len(assessment_links)} potential assessment links")
            
            if len(assessment_links) == 0:
                logger.warning("No assessment links found. Trying alternative extraction methods...")
                assessment_links = self._extract_links_alternative(soup)
                logger.info(f"Alternative method found {len(assessment_links)} links")
            
            # Scrape each assessment page
            for idx, link in enumerate(assessment_links, 1):
                logger.info(f"Scraping assessment {idx}/{len(assessment_links)}: {link}")
                assessment_data = self._scrape_assessment_page(link)
                if assessment_data:
                    self.assessments.append(assessment_data)
                time.sleep(2)  # Be respectful - 2 second delay
            
            logger.info(f"✅ Successfully scraped {len(self.assessments)} assessments")
            
            # Save to file
            if self.assessments:
                self._save_to_file()
            
            return self.assessments
            
        except Exception as e:
            logger.error(f"Error during scraping: {e}", exc_info=True)
            return []
    
    def _fetch_with_retry(self, url: str, max_retries: int = 3) -> Optional[requests.Response]:
        """Fetch URL with retry logic."""
        for attempt in range(max_retries):
            try:
                response = requests.get(url, headers=self.headers, timeout=30)
                response.raise_for_status()
                return response
            except requests.RequestException as e:
                logger.warning(f"Attempt {attempt + 1}/{max_retries} failed for {url}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(5 * (attempt + 1))  # Exponential backoff
        return None
    
    def _extract_assessment_links_comprehensive(self, soup: BeautifulSoup) -> List[str]:
        """Extract all Individual Test Solution links using comprehensive methods."""
        links = set()
        
        # Method 1: Look for product/assessment cards with various class patterns
        selectors = [
            'div[class*="product"]',
            'div[class*="assessment"]',
            'div[class*="card"]',
            'div[class*="item"]',
            'article[class*="product"]',
            'li[class*="product"]',
            'div[class*="solution"]',
            'div[class*="test"]'
        ]
        
        for selector in selectors:
            cards = soup.select(selector)
            logger.info(f"Selector '{selector}' found {len(cards)} elements")
            for card in cards:
                link_tag = card.find('a', href=True)
                if link_tag:
                    href = link_tag['href']
                    full_url = urljoin(self.base_url, href)
                    if self._is_valid_assessment_link(full_url):
                        links.add(full_url)
        
        # Method 2: Look for all links with assessment-related patterns
        all_links = soup.find_all('a', href=True)
        logger.info(f"Total links found on page: {len(all_links)}")
        
        for link in all_links:
            href = link.get('href', '')
            full_url = urljoin(self.base_url, href)
            
            # Check if link matches assessment patterns
            if self._is_valid_assessment_link(full_url):
                links.add(full_url)
        
        # Method 3: Look for structured data (JSON-LD)
        json_ld_scripts = soup.find_all('script', type='application/ld+json')
        for script in json_ld_scripts:
            try:
                data = json.loads(script.string)
                if isinstance(data, dict) and 'url' in data:
                    url = data['url']
                    if self._is_valid_assessment_link(url):
                        links.add(url)
            except:
                pass
        
        return sorted(list(links))
    
    def _extract_links_alternative(self, soup: BeautifulSoup) -> List[str]:
        """Alternative link extraction using text-based matching."""
        links = set()
        all_links = soup.find_all('a', href=True)
        
        # Keywords that indicate an assessment link
        assessment_keywords = [
            'verify', 'reasoning', 'ability', 'personality', 'opq',
            'numerical', 'verbal', 'cognitive', 'judgment', 'situational',
            'mechanical', 'checking', 'calculation', 'aptitude'
        ]
        
        for link in all_links:
            href = link.get('href', '')
            text = link.get_text(strip=True).lower()
            full_url = urljoin(self.base_url, href)
            
            # Check if link text contains assessment keywords
            if any(keyword in text for keyword in assessment_keywords):
                if self._is_valid_assessment_link(full_url):
                    links.add(full_url)
                    logger.info(f"Found assessment by keyword: {text[:50]}")
        
        return sorted(list(links))
    
    def _is_valid_assessment_link(self, url: str) -> bool:
        """Check if URL is a valid assessment link."""
        # Exclude common non-assessment pages
        exclude_patterns = [
            'pre-packaged', 'job-solution', 'blog', 'news', 'contact',
            'about', 'privacy', 'terms', 'cookie', 'login', 'signup',
            'support', 'faq', 'download', '.pdf', '.jpg', '.png',
            'facebook.com', 'twitter.com', 'linkedin.com', 'youtube.com',
            '#', 'mailto:', 'tel:'
        ]
        
        url_lower = url.lower()
        
        # Check if URL should be excluded
        if any(pattern in url_lower for pattern in exclude_patterns):
            return False
        
        # Include patterns that indicate assessment pages
        include_patterns = [
            '/product/', '/assessment/', '/test/', '/solution/',
            'verify', 'reasoning', 'personality', 'cognitive',
            'aptitude', 'ability', 'opq', 'numerical', 'verbal'
        ]
        
        # Must be from SHL domain and match include patterns
        if self.base_url in url and any(pattern in url_lower for pattern in include_patterns):
            return True
        
        return False
    
    def _scrape_assessment_page(self, url: str) -> Optional[Dict]:
        """Scrape individual assessment page for details."""
        try:
            response = self._fetch_with_retry(url)
            if not response:
                return None
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract assessment details
            name = self._extract_name(soup)
            description = self._extract_description(soup)
            test_type = self._extract_test_type(soup, description)
            category = self._extract_category(soup)
            
            # Additional metadata
            metadata = {
                'name': name,
                'url': url,
                'description': description,
                'test_type': test_type,
                'category': category,
                'skills': self._extract_skills(soup, description),
                'duration': self._extract_duration(soup),
                'level': self._extract_level(soup, description),
                'languages': self._extract_languages(soup),
                'format': self._extract_format(soup)
            }
            
            logger.info(f"✓ Extracted: {name}")
            return metadata
            
        except Exception as e:
            logger.error(f"Error scraping {url}: {e}")
            return None
    
    def _extract_name(self, soup: BeautifulSoup) -> str:
        """Extract assessment name."""
        name_tags = [
            soup.find('h1'),
            soup.find('h1', class_=re.compile(r'title|heading|name|product', re.I)),
            soup.find('title'),
            soup.find('meta', property='og:title'),
            soup.find(['h2'], class_=re.compile(r'title|heading|name', re.I))
        ]
        
        for tag in name_tags:
            if tag:
                if tag.name == 'meta':
                    text = tag.get('content', '')
                elif tag.name == 'title':
                    text = tag.get_text(strip=True).split('|')[0].split('-')[0].strip()
                else:
                    text = tag.get_text(strip=True)
                
                if text and len(text) > 0:
                    # Clean up the name
                    text = re.sub(r'\s+', ' ', text)
                    text = text.split('|')[0].split('-')[0].strip()
                    return text
        
        return "Unknown Assessment"
    
    def _extract_description(self, soup: BeautifulSoup) -> str:
        """Extract assessment description."""
        desc_sources = [
            soup.find('meta', {'name': 'description'}),
            soup.find('meta', property='og:description'),
            soup.find(['div', 'p'], class_=re.compile(r'description|summary|intro|overview', re.I)),
            soup.find(['div', 'section'], class_=re.compile(r'content|main', re.I))
        ]
        
        for source in desc_sources:
            if source:
                if source.name == 'meta':
                    text = source.get('content', '')
                else:
                    # Get first paragraph if it's a container
                    first_p = source.find('p')
                    text = first_p.get_text(strip=True) if first_p else source.get_text(strip=True)
                
                if text and len(text) > 50:
                    # Clean up
                    text = re.sub(r'\s+', ' ', text)
                    return text[:500]  # Limit length
        
        return ""
    
    def _extract_test_type(self, soup: BeautifulSoup, description: str) -> str:
        """Extract test type (K=Knowledge, P=Personality, C=Cognitive, S=Situational)."""
        text = (soup.get_text() + ' ' + description).lower()
        
        type_patterns = {
            'P': ['personality', 'behavior', 'trait', 'opq', 'motivational', 'preference'],
            'C': ['cognitive', 'ability', 'reasoning', 'numerical', 'verbal', 'logical', 'aptitude', 'inductive', 'deductive'],
            'K': ['knowledge', 'skill', 'technical', 'coding', 'programming', 'proficiency'],
            'S': ['situational', 'judgment', 'sjt', 'scenario']
        }
        
        for test_type, keywords in type_patterns.items():
            if any(keyword in text for keyword in keywords):
                return test_type
        
        return "O"  # Other
    
    def _extract_category(self, soup: BeautifulSoup) -> str:
        """Extract assessment category."""
        # Look for category badges or tags
        category_elements = soup.find_all(['span', 'div', 'a', 'label'], 
                                         class_=re.compile(r'category|tag|badge|label|type', re.I))
        
        for elem in category_elements:
            text = elem.get_text(strip=True)
            if text and 3 < len(text) < 50:
                return text
        
        # Look in breadcrumbs
        breadcrumbs = soup.find(['nav', 'ol', 'ul'], class_=re.compile(r'breadcrumb', re.I))
        if breadcrumbs:
            items = breadcrumbs.find_all(['a', 'span'])
            if len(items) > 1:
                return items[-2].get_text(strip=True)
        
        return "General"
    
    def _extract_skills(self, soup: BeautifulSoup, description: str) -> List[str]:
        """Extract skills assessed."""
        text = (soup.get_text() + ' ' + description).lower()
        
        skill_keywords = [
            'leadership', 'communication', 'teamwork', 'problem-solving',
            'analytical', 'critical thinking', 'decision making', 'planning',
            'numerical reasoning', 'verbal reasoning', 'logical thinking',
            'attention to detail', 'customer service', 'sales', 'management',
            'technical', 'coding', 'data analysis', 'creativity', 'innovation'
        ]
        
        found_skills = [skill for skill in skill_keywords if skill in text]
        return found_skills[:7]  # Limit to top 7
    
    def _extract_duration(self, soup: BeautifulSoup) -> str:
        """Extract test duration."""
        text = soup.get_text()
        
        # Look for patterns like "30 minutes", "1 hour", "45 mins", "1.5 hours"
        patterns = [
            r'(\d+(?:\.\d+)?)\s*(?:hour|hr)s?',
            r'(\d+)\s*(?:minute|min)s?',
            r'duration[:\s]+(\d+\s*(?:minute|min|hour|hr)s?)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.I)
            if match:
                return match.group(0).strip()
        
        return "N/A"
    
    def _extract_level(self, soup: BeautifulSoup, description: str) -> str:
        """Extract target job level."""
        text = (soup.get_text() + ' ' + description).lower()
        
        level_patterns = {
            'Senior': ['senior', 'executive', 'leadership', 'director', 'c-level'],
            'Mid-Level': ['mid-level', 'intermediate', 'experienced', 'professional'],
            'Entry-Level': ['entry', 'junior', 'graduate', 'early career']
        }
        
        for level, keywords in level_patterns.items():
            if any(keyword in text for keyword in keywords):
                return level
        
        return "All Levels"
    
    def _extract_languages(self, soup: BeautifulSoup) -> List[str]:
        """Extract available languages."""
        text = soup.get_text().lower()
        
        common_languages = ['english', 'spanish', 'french', 'german', 'chinese', 
                           'japanese', 'portuguese', 'arabic', 'hindi', 'dutch']
        
        found_languages = [lang for lang in common_languages if lang in text]
        return found_languages if found_languages else ['English']
    
    def _extract_format(self, soup: BeautifulSoup) -> str:
        """Extract assessment format (online, adaptive, etc.)."""
        text = soup.get_text().lower()
        
        if 'adaptive' in text:
            return 'Adaptive'
        elif 'online' in text or 'digital' in text:
            return 'Online'
        elif 'paper' in text or 'pencil' in text:
            return 'Paper-based'
        
        return 'Online'
    
    def _save_to_file(self, filename: str = 'data/shl_assessments.json'):
        """Save scraped data to JSON file."""
        import os
        os.makedirs('data', exist_ok=True)
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.assessments, f, indent=2, ensure_ascii=False)
        logger.info(f"💾 Saved {len(self.assessments)} assessments to {filename}")
    
    def load_from_file(self, filename: str = 'data/shl_assessments.json') -> List[Dict]:
        """Load previously scraped data from file."""
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                self.assessments = json.load(f)
            logger.info(f"📂 Loaded {len(self.assessments)} assessments from {filename}")
            return self.assessments
        except FileNotFoundError:
            logger.error(f"File {filename} not found")
            return []


def main():
    """Main execution function."""
    scraper = SHLScraper()
    
    print("\n" + "="*70)
    print("SHL PRODUCT CATALOG SCRAPER")
    print("="*70 + "\n")
    
    # Check robots.txt first
    print("⚙️  Checking robots.txt compliance...")
    can_scrape = scraper.check_robots_txt()
    
    if not can_scrape:
        print("\n❌ SCRAPING IS BLOCKED BY ROBOTS.TXT")
        print("\n📋 ALTERNATIVE DATA COLLECTION METHODS:")
        print("\n1. MANUAL BROWSER EXTRACTION:")
        print("   - Visit the SHL catalog page")
        print("   - Use browser DevTools Console:")
        print("   - Run: Array.from(document.querySelectorAll('a')).map(a => a.href)")
        print("\n2. SELENIUM/PLAYWRIGHT:")
        print("   - Use headless browser with human-like behavior")
        print("   - Respects JavaScript-rendered content")
        print("\n3. OFFICIAL API:")
        print("   - Contact SHL for official API access")
        print("   - Request data partnership")
        print("\n4. PUBLIC DOCUMENTATION:")
        print("   - Use SHL's public brochures and PDFs")
        print("   - Extract data from official documentation")
        print("\n" + "="*70)
        
        # Ask user if they want to proceed anyway
        response = input("\nProceed with scraping anyway? (yes/no): ").strip().lower()
        if response != 'yes':
            print("Exiting...")
            return
    
    # Scrape the catalog
    assessments = scraper.scrape_catalog(respect_robots=False)
    
    print(f"\n{'='*70}")
    print(f"SCRAPING COMPLETE!")
    print(f"Total assessments scraped: {len(assessments)}")
    print(f"{'='*70}\n")
    
    # Display statistics
    if assessments:
        print("📊 STATISTICS:")
        test_types = {}
        for a in assessments:
            t = a.get('test_type', 'O')
            test_types[t] = test_types.get(t, 0) + 1
        
        for test_type, count in sorted(test_types.items()):
            type_names = {'C': 'Cognitive', 'P': 'Personality', 'K': 'Knowledge', 'S': 'Situational', 'O': 'Other'}
            print(f"  {type_names.get(test_type, 'Other')}: {count}")
        
        print("\n📝 SAMPLE ASSESSMENTS:")
        for i, assessment in enumerate(assessments[:3], 1):
            print(f"\n{i}. {assessment['name']}")
            print(f"   Type: {assessment['test_type']}")
            print(f"   URL: {assessment['url'][:60]}...")
            if assessment['description']:
                print(f"   Description: {assessment['description'][:100]}...")
    else:
        print("⚠️  No assessments were scraped. Check the logs for errors.")

if __name__ == "__main__":
    main()