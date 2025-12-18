"""
Complete SHL Product Catalog Scraper
This scraper extracts all 377 assessments from SHL's product catalog
Uses API-style approach to fetch paginated data
"""
import requests
from bs4 import BeautifulSoup
import json
import time
import re
from typing import List, Dict, Optional
import logging
from urllib.parse import urljoin, urlparse, parse_qs

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CompleteSHLScraper:
    def __init__(self):
        self.base_url = "https://www.shl.com"
        self.catalog_url = "https://www.shl.com/solutions/products/product-catalog/"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        self.assessments = []
        self.assessment_links = set()
    
    def scrape_all_assessments(self) -> List[Dict]:
        """
        Main method to scrape all 377 assessments.
        Strategy: 
        1. Scrape catalog with pagination
        2. Extract all product links
        3. Scrape each product page
        """
        logger.info("🚀 Starting complete SHL catalog scrape...")
        
        try:
            # Step 1: Get all assessment links from catalog (with pagination)
            self._scrape_catalog_pages()
            
            logger.info(f"📋 Found {len(self.assessment_links)} unique assessment links")
            
            if len(self.assessment_links) == 0:
                logger.error("❌ No assessment links found. Trying alternative method...")
                self._try_alternative_discovery()
            
            # Step 2: Scrape each assessment page
            self._scrape_all_assessment_pages()
            
            # Step 3: Save results
            if self.assessments:
                self._save_to_file()
            
            logger.info(f"✅ Successfully scraped {len(self.assessments)} assessments")
            return self.assessments
            
        except Exception as e:
            logger.error(f"❌ Error during scraping: {e}", exc_info=True)
            return self.assessments
    
    def _scrape_catalog_pages(self):
        """Scrape catalog with pagination to get all product links."""
        logger.info("📄 Scraping catalog pages...")
        
        # Try different pagination strategies
        
        # Strategy 1: Standard pagination (start parameter)
        for start in range(0, 400, 12):  # 377 products, 12 per page typically
            url = f"{self.catalog_url}?start={start}"
            logger.info(f"Fetching page starting at {start}...")
            
            try:
                response = self.session.get(url, timeout=30)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.content, 'html.parser')
                links = self._extract_product_links_from_page(soup)
                
                if not links:
                    logger.info(f"No more products found at start={start}")
                    break
                
                self.assessment_links.update(links)
                logger.info(f"   Found {len(links)} links (Total: {len(self.assessment_links)})")
                
                time.sleep(1)  # Be respectful
                
            except Exception as e:
                logger.warning(f"Error fetching page start={start}: {e}")
                continue
        
        # Strategy 2: Try with type parameter (type=1 for individual assessments)
        if len(self.assessment_links) < 100:
            logger.info("Trying with type parameter...")
            for start in range(0, 400, 12):
                url = f"{self.catalog_url}?type=1&start={start}"
                try:
                    response = self.session.get(url, timeout=30)
                    soup = BeautifulSoup(response.content, 'html.parser')
                    links = self._extract_product_links_from_page(soup)
                    if not links:
                        break
                    self.assessment_links.update(links)
                    time.sleep(1)
                except:
                    continue
    
    def _extract_product_links_from_page(self, soup: BeautifulSoup) -> set:
        """Extract all product links from a catalog page."""
        links = set()
        
        # Method 1: Find links with /view/ pattern (product detail pages)
        for link in soup.find_all('a', href=True):
            href = link.get('href', '')
            
            # Product detail pages have pattern: /products/product-catalog/view/product-name/
            if '/product-catalog/view/' in href or '/products/product-catalog/view/' in href:
                full_url = urljoin(self.base_url, href)
                # Filter out non-product pages
                if not any(x in href.lower() for x in ['javascript:', '#', 'mailto:', '.pdf', '.jpg']):
                    links.add(full_url)
        
        # Method 2: Look for product cards/containers
        product_containers = soup.find_all(['div', 'article', 'li'], class_=re.compile(r'product|item|card', re.I))
        for container in product_containers:
            link = container.find('a', href=True)
            if link:
                href = link['href']
                if '/view/' in href:
                    full_url = urljoin(self.base_url, href)
                    links.add(full_url)
        
        return links
    
    def _try_alternative_discovery(self):
        """Try alternative methods to discover all product URLs."""
        logger.info("🔍 Trying alternative discovery methods...")
        
        # Method 1: Try to find sitemap
        sitemap_urls = [
            f"{self.base_url}/sitemap.xml",
            f"{self.base_url}/sitemap_index.xml",
            f"{self.base_url}/products-sitemap.xml"
        ]
        
        for sitemap_url in sitemap_urls:
            try:
                response = self.session.get(sitemap_url, timeout=30)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.content, 'xml')
                    urls = soup.find_all('loc')
                    for url in urls:
                        url_text = url.get_text()
                        if '/product-catalog/view/' in url_text:
                            self.assessment_links.add(url_text)
                    logger.info(f"Found {len(urls)} URLs from sitemap")
            except:
                continue
        
        # Method 2: Try common product name patterns
        # Based on search results, we know products have names like:
        # - "chemical-engineering-new"
        # - "microsoft-excel-365-new"
        # - "workplace-health-and-safety-new"
        # This method is less reliable but can help
        
        logger.info(f"Alternative discovery found {len(self.assessment_links)} additional links")
    
    def _scrape_all_assessment_pages(self):
        """Scrape all individual assessment pages."""
        logger.info(f"📖 Scraping {len(self.assessment_links)} assessment pages...")
        
        total = len(self.assessment_links)
        for idx, url in enumerate(sorted(self.assessment_links), 1):
            logger.info(f"[{idx}/{total}] Scraping: {url}")
            
            assessment_data = self._scrape_assessment_page(url)
            if assessment_data:
                self.assessments.append(assessment_data)
            
            # Progress report every 50 items
            if idx % 50 == 0:
                logger.info(f"📊 Progress: {idx}/{total} ({(idx/total)*100:.1f}%) - {len(self.assessments)} successful")
            
            time.sleep(1.5)  # Be respectful to the server
    
    def _scrape_assessment_page(self, url: str) -> Optional[Dict]:
        """Scrape individual assessment page for complete details."""
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract all data fields
            metadata = {
                'name': self._extract_name(soup),
                'url': url,
                'description': self._extract_description(soup),
                'test_type': self._extract_test_type(soup),
                'category': self._extract_category(soup),
                'job_levels': self._extract_job_levels(soup),
                'languages': self._extract_languages(soup),
                'duration': self._extract_duration(soup),
                'remote_testing': self._extract_remote_testing(soup),
                'industries': self._extract_industries(soup),
                'competencies': self._extract_competencies(soup),
                'reports_available': self._extract_reports(soup)
            }
            
            # Only return if we got a valid name
            if metadata['name'] != "Unknown Assessment":
                logger.debug(f"✓ Extracted: {metadata['name']}")
                return metadata
            else:
                logger.warning(f"⚠️  Failed to extract name from {url}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error scraping {url}: {e}")
            return None
    
    def _extract_name(self, soup: BeautifulSoup) -> str:
        """Extract assessment name."""
        # Try multiple selectors in order of preference
        selectors = [
            ('h1', None),
            ('h1', {'class': re.compile(r'title|heading|name', re.I)}),
            ('meta', {'property': 'og:title'}),
            ('title', None),
        ]
        
        for tag_name, attrs in selectors:
            element = soup.find(tag_name, attrs)
            if element:
                if tag_name == 'meta':
                    text = element.get('content', '')
                elif tag_name == 'title':
                    text = element.get_text(strip=True)
                    # Remove site name from title
                    text = re.split(r'\||–|-', text)[0].strip()
                else:
                    text = element.get_text(strip=True)
                
                if text and len(text) > 0:
                    # Clean up
                    text = re.sub(r'\s+', ' ', text).strip()
                    return text
        
        return "Unknown Assessment"
    
    def _extract_description(self, soup: BeautifulSoup) -> str:
        """Extract detailed description."""
        # Try meta description first
        meta_desc = soup.find('meta', {'name': 'description'})
        if meta_desc and meta_desc.get('content'):
            return meta_desc['content'].strip()
        
        # Try og:description
        og_desc = soup.find('meta', {'property': 'og:description'})
        if og_desc and og_desc.get('content'):
            return og_desc['content'].strip()
        
        # Look for description paragraphs
        desc_containers = soup.find_all(['div', 'section'], class_=re.compile(r'description|summary|overview|content', re.I))
        for container in desc_containers:
            paragraphs = container.find_all('p')
            if paragraphs:
                text = ' '.join(p.get_text(strip=True) for p in paragraphs[:2])
                if len(text) > 100:
                    return text[:1000]
        
        # Fallback: get first substantial paragraph
        paragraphs = soup.find_all('p')
        for p in paragraphs:
            text = p.get_text(strip=True)
            if len(text) > 100:
                return text[:1000]
        
        return ""
    
    def _extract_test_type(self, soup: BeautifulSoup) -> str:
        """Extract test type code."""
        # Look for "Test Type:" label
        text = soup.get_text()
        match = re.search(r'Test Type:\s*([A-Z\s]+)', text, re.I)
        if match:
            return match.group(1).strip()
        
        # Fallback: infer from content
        text_lower = text.lower()
        if any(w in text_lower for w in ['personality', 'opq', 'behavior', 'trait']):
            return "P"
        elif any(w in text_lower for w in ['cognitive', 'ability', 'reasoning', 'aptitude']):
            return "A"
        elif any(w in text_lower for w in ['knowledge', 'skill', 'technical']):
            return "K"
        elif any(w in text_lower for w in ['biodata', 'situational', 'judgment']):
            return "B"
        elif any(w in text_lower for w in ['simulation', 'exercise']):
            return "S"
        
        return "Unknown"
    
    def _extract_category(self, soup: BeautifulSoup) -> List[str]:
        """Extract categories/tags."""
        categories = []
        
        # Look for category badges/tags
        for elem in soup.find_all(['span', 'div', 'a'], class_=re.compile(r'category|tag|badge', re.I)):
            text = elem.get_text(strip=True)
            if text and 3 < len(text) < 50:
                categories.append(text)
        
        return categories if categories else ["General"]
    
    def _extract_job_levels(self, soup: BeautifulSoup) -> List[str]:
        """Extract target job levels."""
        levels = []
        text = soup.get_text()
        
        # Common job level keywords
        level_keywords = [
            'Entry-Level', 'Graduate', 'Mid-Professional', 'Professional Individual Contributor',
            'Manager', 'Director', 'Executive', 'Supervisor', 'Front Line Manager'
        ]
        
        for level in level_keywords:
            if level in text:
                levels.append(level)
        
        return levels if levels else ["General Population"]
    
    def _extract_languages(self, soup: BeautifulSoup) -> List[str]:
        """Extract available languages."""
        languages = []
        text = soup.get_text()
        
        # Common languages in SHL
        language_patterns = [
            'English (USA)', 'English (International)', 'Spanish', 'French', 'German',
            'Chinese Simplified', 'Chinese Traditional', 'Japanese', 'Italian', 'Portuguese',
            'Dutch', 'Swedish', 'Norwegian', 'Danish', 'Finnish', 'Turkish', 'Arabic',
            'Korean', 'Indonesian', 'Thai', 'Polish', 'Romanian', 'Russian', 'Czech'
        ]
        
        for lang in language_patterns:
            if lang in text:
                languages.append(lang)
        
        return languages if languages else ["English (USA)"]
    
    def _extract_duration(self, soup: BeautifulSoup) -> str:
        """Extract test duration."""
        text = soup.get_text()
        
        # Look for "Approximate Completion Time" pattern
        match = re.search(r'Approximate Completion Time[^=]*=\s*(\d+)\s*minutes?', text, re.I)
        if match:
            return f"{match.group(1)} minutes"
        
        # Look for general duration patterns
        match = re.search(r'(\d+)\s*(?:minute|min)s?', text, re.I)
        if match:
            return f"{match.group(1)} minutes"
        
        return "N/A"
    
    def _extract_remote_testing(self, soup: BeautifulSoup) -> bool:
        """Check if remote testing is available."""
        text = soup.get_text()
        return 'Remote Testing' in text or 'remote testing' in text.lower()
    
    def _extract_industries(self, soup: BeautifulSoup) -> List[str]:
        """Extract applicable industries."""
        industries = []
        text = soup.get_text()
        
        industry_keywords = [
            'Banking/Finance', 'Healthcare', 'Insurance', 'Retail', 'Manufacturing',
            'Information Technology', 'Telecommunications', 'Hospitality', 'Customer Service'
        ]
        
        for industry in industry_keywords:
            if industry in text:
                industries.append(industry)
        
        return industries
    
    def _extract_competencies(self, soup: BeautifulSoup) -> List[str]:
        """Extract measured competencies/skills."""
        competencies = []
        text = soup.get_text().lower()
        
        competency_keywords = [
            'leadership', 'communication', 'teamwork', 'problem solving',
            'analytical thinking', 'decision making', 'planning', 'organizing',
            'customer focus', 'adaptability', 'numerical reasoning', 'verbal reasoning'
        ]
        
        for comp in competency_keywords:
            if comp in text:
                competencies.append(comp.title())
        
        return competencies[:10]  # Limit to top 10
    
    def _extract_reports(self, soup: BeautifulSoup) -> List[str]:
        """Extract available report types."""
        reports = []
        
        # Look for links to report PDFs or report mentions
        for link in soup.find_all('a', href=True):
            href = link.get('href', '').lower()
            text = link.get_text(strip=True)
            
            if 'report' in href or 'report' in text.lower():
                if text and len(text) < 100:
                    reports.append(text)
        
        return list(set(reports))[:5]  # Unique, limit to 5
    
    def _save_to_file(self, filename: str = 'data/shl_assessments.json'):
        """Save scraped data to JSON file."""
        import os
        os.makedirs('data', exist_ok=True)
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.assessments, f, indent=2, ensure_ascii=False)
        
        logger.info(f"💾 Saved {len(self.assessments)} assessments to {filename}")
        
        # Also save a summary
        summary = {
            'total_assessments': len(self.assessments),
            'test_types': {},
            'languages': set(),
            'job_levels': set()
        }
        
        for assessment in self.assessments:
            # Count test types
            test_type = assessment.get('test_type', 'Unknown')
            summary['test_types'][test_type] = summary['test_types'].get(test_type, 0) + 1
            
            # Collect languages
            summary['languages'].update(assessment.get('languages', []))
            
            # Collect job levels
            summary['job_levels'].update(assessment.get('job_levels', []))
        
        # Convert sets to lists for JSON
        summary['languages'] = sorted(list(summary['languages']))
        summary['job_levels'] = sorted(list(summary['job_levels']))
        
        with open('data/shl_summary.json', 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        
        logger.info(f"📊 Saved summary to data/shl_summary.json")


def main():
    """Main execution function."""
    print("\n" + "="*80)
    print(" " * 20 + "SHL COMPLETE CATALOG SCRAPER")
    print(" " * 25 + "Target: 377 Assessments")
    print("="*80 + "\n")
    
    scraper = CompleteSHLScraper()
    
    # Run the scraper
    assessments = scraper.scrape_all_assessments()
    
    # Print results
    print("\n" + "="*80)
    print(" " * 30 + "SCRAPING COMPLETE!")
    print("="*80)
    print(f"\n📊 RESULTS:")
    print(f"   Total assessments scraped: {len(assessments)}")
    print(f"   Target was: 377")
    print(f"   Success rate: {(len(assessments)/377)*100:.1f}%")
    
    if assessments:
        # Display statistics
        test_types = {}
        for a in assessments:
            t = a.get('test_type', 'Unknown')
            test_types[t] = test_types.get(t, 0) + 1
        
        print(f"\n📈 TEST TYPE BREAKDOWN:")
        for test_type, count in sorted(test_types.items(), key=lambda x: x[1], reverse=True):
            print(f"   {test_type:20} : {count:3} ({(count/len(assessments))*100:5.1f}%)")
        
        print(f"\n📝 SAMPLE ASSESSMENTS:")
        for i, assessment in enumerate(assessments[:5], 1):
            print(f"\n   {i}. {assessment['name']}")
            print(f"      Type: {assessment.get('test_type', 'N/A')}")
            print(f"      Duration: {assessment.get('duration', 'N/A')}")
            print(f"      Languages: {len(assessment.get('languages', []))} available")
            print(f"      URL: {assessment['url'][:70]}...")
        
        print(f"\n💾 Data saved to: data/shl_assessments.json")
        print(f"📊 Summary saved to: data/shl_summary.json")
    else:
        print("\n⚠️  WARNING: No assessments were scraped!")
        print("\nPossible reasons:")
        print("   1. Website structure has changed")
        print("   2. Rate limiting or blocking")
        print("   3. Network issues")
        print("\nTry:")
        print("   - Running with VPN")
        print("   - Using Selenium (see shl_selenium_scraper artifact)")
        print("   - Increasing delays between requests")
    
    print("\n" + "="*80 + "\n")


if __name__ == "__main__":
    main()