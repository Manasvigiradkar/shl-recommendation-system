"""
SHL Product Catalog Web Scraper
Scrapes assessment data from SHL website
"""
import requests
from bs4 import BeautifulSoup
import json
import time
from typing import List, Dict
import re

class SHLScraper:
    def __init__(self):
        self.base_url = "https://www.shl.com/solutions/products/product-catalog/"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        self.assessments = []
        
    def scrape_catalog(self) -> List[Dict]:
        """Main scraping method to get all Individual Test Solutions."""
        print("Starting SHL catalog scrape...")
        
        try:
            # Fetch the main catalog page
            response = requests.get(self.base_url, headers=self.headers, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find all assessment links
            # This is a simplified example - you'll need to inspect the actual HTML structure
            assessment_links = self._extract_assessment_links(soup)
            
            print(f"Found {len(assessment_links)} potential assessment links")
            
            # Scrape each assessment page
            for idx, link in enumerate(assessment_links, 1):
                print(f"Scraping assessment {idx}/{len(assessment_links)}: {link}")
                assessment_data = self._scrape_assessment_page(link)
                if assessment_data:
                    self.assessments.append(assessment_data)
                time.sleep(1)  # Be respectful to the server
            
            print(f"Successfully scraped {len(self.assessments)} assessments")
            
            # Save to file
            self._save_to_file()
            
            return self.assessments
            
        except Exception as e:
            print(f"Error during scraping: {e}")
            return []
    
    def _extract_assessment_links(self, soup: BeautifulSoup) -> List[str]:
        """Extract all Individual Test Solution links from the catalog page."""
        links = []
        
        # Method 1: Look for assessment cards or product listings
        # Adjust selectors based on actual HTML structure
        product_cards = soup.find_all(['div', 'a'], class_=re.compile(r'product|assessment|card', re.I))
        
        for card in product_cards:
            link = card.get('href') or (card.find('a') and card.find('a').get('href'))
            if link:
                # Filter out "Pre-packaged Job Solutions"
                if 'pre-packaged' not in link.lower() and 'job-solution' not in link.lower():
                    full_link = link if link.startswith('http') else f"https://www.shl.com{link}"
                    links.append(full_link)
        
        # Method 2: Look for specific patterns in links
        all_links = soup.find_all('a', href=True)
        for link in all_links:
            href = link.get('href', '')
            # Look for product/assessment pages
            if '/product/' in href or '/assessment/' in href or '/test/' in href:
                if 'pre-packaged' not in href.lower():
                    full_link = href if href.startswith('http') else f"https://www.shl.com{href}"
                    if full_link not in links:
                        links.append(full_link)
        
        return list(set(links))  # Remove duplicates
    
    def _scrape_assessment_page(self, url: str) -> Dict:
        """Scrape individual assessment page for details."""
        try:
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract assessment details
            # Adjust selectors based on actual HTML structure
            
            # Name
            name = self._extract_name(soup)
            
            # Description
            description = self._extract_description(soup)
            
            # Test Type
            test_type = self._extract_test_type(soup, description)
            
            # Category
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
                'level': self._extract_level(soup, description)
            }
            
            return metadata
            
        except Exception as e:
            print(f"Error scraping {url}: {e}")
            return None
    
    def _extract_name(self, soup: BeautifulSoup) -> str:
        """Extract assessment name."""
        # Try multiple selectors
        name_tags = [
            soup.find('h1'),
            soup.find('title'),
            soup.find(['h1', 'h2'], class_=re.compile(r'title|name|heading', re.I))
        ]
        
        for tag in name_tags:
            if tag and tag.get_text(strip=True):
                return tag.get_text(strip=True).split('|')[0].strip()
        
        return "Unknown Assessment"
    
    def _extract_description(self, soup: BeautifulSoup) -> str:
        """Extract assessment description."""
        desc_tags = [
            soup.find('meta', {'name': 'description'}),
            soup.find(['p', 'div'], class_=re.compile(r'description|summary|intro', re.I)),
            soup.find('p')
        ]
        
        for tag in desc_tags:
            if tag:
                if tag.name == 'meta':
                    return tag.get('content', '')
                text = tag.get_text(strip=True)
                if len(text) > 50:
                    return text
        
        return ""
    
    def _extract_test_type(self, soup: BeautifulSoup, description: str) -> str:
        """Extract test type (K=Knowledge, P=Personality, C=Cognitive, etc.)."""
        text = (soup.get_text() + ' ' + description).lower()
        
        if any(word in text for word in ['personality', 'behavior', 'trait', 'opq']):
            return "P"
        elif any(word in text for word in ['cognitive', 'ability', 'reasoning', 'numerical', 'verbal']):
            return "C"
        elif any(word in text for word in ['knowledge', 'skill', 'technical', 'coding', 'programming']):
            return "K"
        elif any(word in text for word in ['situational', 'judgment', 'sjt']):
            return "S"
        
        return "O"  # Other
    
    def _extract_category(self, soup: BeautifulSoup) -> str:
        """Extract assessment category."""
        category_tags = soup.find_all(['span', 'div', 'a'], class_=re.compile(r'category|tag|label', re.I))
        
        for tag in category_tags:
            text = tag.get_text(strip=True)
            if text and len(text) < 50:
                return text
        
        return "General"
    
    def _extract_skills(self, soup: BeautifulSoup, description: str) -> List[str]:
        """Extract skills mentioned in the assessment."""
        text = (soup.get_text() + ' ' + description).lower()
        
        skill_keywords = [
            'java', 'python', 'javascript', 'sql', 'leadership', 'communication',
            'teamwork', 'problem-solving', 'analytical', 'collaboration', 'management',
            'programming', 'coding', 'data analysis', 'critical thinking'
        ]
        
        found_skills = [skill for skill in skill_keywords if skill in text]
        return found_skills[:5]  # Limit to top 5
    
    def _extract_duration(self, soup: BeautifulSoup) -> str:
        """Extract test duration if available."""
        text = soup.get_text()
        
        # Look for patterns like "30 minutes", "1 hour", etc.
        duration_pattern = re.search(r'(\d+)\s*(minute|min|hour|hr)s?', text, re.I)
        if duration_pattern:
            return duration_pattern.group(0)
        
        return "N/A"
    
    def _extract_level(self, soup: BeautifulSoup, description: str) -> str:
        """Extract job level (entry, mid, senior, etc.)."""
        text = (soup.get_text() + ' ' + description).lower()
        
        if any(word in text for word in ['senior', 'executive', 'leadership']):
            return "Senior"
        elif any(word in text for word in ['mid-level', 'intermediate', 'experienced']):
            return "Mid-Level"
        elif any(word in text for word in ['entry', 'junior', 'graduate']):
            return "Entry-Level"
        
        return "All Levels"
    
    def _save_to_file(self, filename: str = 'shl_assessments.json'):
        """Save scraped data to JSON file."""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.assessments, f, indent=2, ensure_ascii=False)
        print(f"Saved {len(self.assessments)} assessments to {filename}")
    
    def load_from_file(self, filename: str = 'shl_assessments.json') -> List[Dict]:
        """Load previously scraped data from file."""
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                self.assessments = json.load(f)
            print(f"Loaded {len(self.assessments)} assessments from {filename}")
            return self.assessments
        except FileNotFoundError:
            print(f"File {filename} not found")
            return []

def main():
    """Main execution function."""
    scraper = SHLScraper()
    
    # Scrape the catalog
    assessments = scraper.scrape_catalog()
    
    print(f"\n{'='*50}")
    print(f"Scraping Complete!")
    print(f"Total assessments scraped: {len(assessments)}")
    print(f"{'='*50}\n")
    
    # Display sample
    if assessments:
        print("Sample assessment:")
        print(json.dumps(assessments[0], indent=2))

if __name__ == "__main__":
    main()