import pandas as pd
import time
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from datetime import datetime
import os

class TCASEngineeringScraper:
    def __init__(self):
        self.data = []
        self.processing_data = []
        self.driver = self._setup_driver()
        
        # Common selectors and patterns
        self.course_selectors = ["h1", "h2", ".course-name", ".program-name", "[class*='title']", "[class*='name']"]
        self.uni_selectors = [".university-name", ".institution-name", "[class*='university']", "[class*='institution']"]
        self.fee_patterns = [
            r'ค่าเทอม[:\s]*(\d+(?:,\d+)*)\s*บาท',
            r'ค่าใช้จ่าย[:\s]*(\d+(?:,\d+)*)\s*บาท',
            r'อัตราค่าเทอม[:\s]*(\d+(?:,\d+)*)\s*บาท',
            r'(\d+(?:,\d+)*)\s*บาท[/\s]*เทอม'
        ]
        self.course_type_patterns = [
            r'ประเภทหลักสูตร[:\s]*([^\n]+)',
            r'(ภาษาไทย|ภาษาอังกฤษ|นานาชาติ|ปกติ|พิเศษ|International)'
        ]
        self.cost_patterns = [
            r'ค่าใช้จ่าย[:\s]*([^\n]+)',
            r'(\d+(?:,\d+)*\s*(?:บาท|บ\.)[^\n]*(?:เทอม|ภาค|ปี))'
        ]
    
    def _setup_driver(self):
        """Setup Chrome driver with options"""
        options = Options()
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        
        try:
            driver = webdriver.Chrome(options=options)
            print("Chrome driver initialized successfully")
            return driver
        except Exception as e:
            print(f"Error initializing Chrome driver: {e}")
            return None
    
    def _wait_and_find(self, by, value, timeout=10):
        """Helper method to wait for element and find it"""
        try:
            return WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
        except:
            return None
    
    def _extract_by_selectors(self, selectors, condition=None):
        """Extract text using multiple selectors with optional condition"""
        for selector in selectors:
            elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
            for element in elements:
                text = element.text.strip()
                if text and (not condition or condition(text)):
                    return text
        return "N/A"
    
    def _extract_by_patterns(self, page_text, patterns, max_length=200):
        """Extract text using regex patterns"""
        for pattern in patterns:
            matches = re.findall(pattern, page_text, re.IGNORECASE)
            if matches:
                for match in matches:
                    if len(match.strip()) < max_length:
                        return match.strip()
        return "N/A"
    
    def search_engineering_programs(self, keywords):
        """Search for engineering programs using keywords"""
        if not self.driver:
            return []
        
        all_results = []
        
        for keyword in keywords:
            print(f"Searching for: {keyword}")
            try:
                self.driver.get("https://course.mytcas.com")
                time.sleep(3)
                
                # Search
                search_box = self._wait_and_find(By.CSS_SELECTOR, "input[placeholder*='วิชา'], input[type='text']")
                if search_box:
                    search_box.clear()
                    search_box.send_keys(keyword)
                    search_box.send_keys(Keys.RETURN)
                    time.sleep(5)
                
                # Get results
                course_links = self.driver.find_elements(By.CSS_SELECTOR, "a[href*='course'], a[href*='program']")
                
                for link in course_links:
                    try:
                        url = link.get_attribute("href")
                        title = link.text.strip()
                        
                        # Filter engineering programs
                        if url and title and any(eng in title.lower() for eng in ['วิศวกรรม', 'engineering', 'วศ.บ']):
                            all_results.append({'title': title, 'url': url, 'keyword': keyword})
                    except:
                        continue
                        
            except Exception as e:
                print(f"Error searching {keyword}: {e}")
        
        # Remove duplicates
        unique_results = []
        seen_urls = set()
        for result in all_results:
            if result['url'] not in seen_urls:
                unique_results.append(result)
                seen_urls.add(result['url'])
        
        print(f"Found {len(unique_results)} unique programs")
        return unique_results
    
    def extract_course_info(self, url):
        """Extract all course information in one pass"""
        try:
            self.driver.get(url)
            time.sleep(3)
            
            if not self._wait_and_find(By.TAG_NAME, "body"):
                return None, None
            
            page_text = self.driver.find_element(By.TAG_NAME, "body").text
            
            # Extract course name
            course_name = self._extract_by_selectors(
                self.course_selectors, 
                lambda x: len(x) > 10
            )
            
            # Extract university
            university = self._extract_by_selectors(
                self.uni_selectors,
                lambda x: 'มหาวิทยาลัย' in x or 'university' in x.lower() or 'สถาบัน' in x
            )
            
            # If not found, try regex
            if university == "N/A":
                uni_match = re.search(r'([^.\n]*(?:มหาวิทยาลัย|สถาบัน)[^.\n]*)', page_text)
                if uni_match and len(uni_match.group(1).strip()) < 100:
                    university = uni_match.group(1).strip()
            
            # Extract course type
            course_type = self._extract_by_patterns(page_text, self.course_type_patterns, 50)
            
            # Extract cost info
            cost_matches = []
            for pattern in self.cost_patterns:
                matches = re.findall(pattern, page_text, re.IGNORECASE)
                cost_matches.extend([m for m in matches if len(m.strip()) < 200])
            
            cost_info = ' | '.join(list(set(cost_matches))[:3]) if cost_matches else "N/A"
            
            # Extract tuition fee
            fee_text = self._extract_by_patterns(page_text, self.fee_patterns)
            
            # Processing info
            processing_info = {
                'มหาวิทยาลัย': university,
                'หลักสูตร': course_name,
                'ประเภทหลักสูตร': course_type,
                'ค่าใช้จ่าย': cost_info,
                'URL': url
            }
            
            # Main data
            main_data = {
                'university': university,
                'course_name': course_name,
                'tuition_fee': fee_text,
                'url': url
            }
            
            return processing_info, main_data
            
        except Exception as e:
            print(f"Error extracting from {url}: {e}")
            return None, None
    
    def parse_tuition_fee(self, fee_text, page_context=""):
        """Parse and normalize tuition fee"""
        if not fee_text or fee_text == "N/A":
            return None
        
        try:
            amount = int(fee_text.replace(',', ''))
            
            # Convert to semester fee
            if any(keyword in page_context for keyword in ['ปี', 'year']):
                amount //= 2
            elif any(keyword in page_context for keyword in ['หลักสูตร', 'program']):
                amount //= 8
            
            return amount
        except:
            return None
    
    def scrape_engineering_programs(self):
        """Main scraping function"""
        keywords = ["วิศวกรรมคอมพิวเตอร์", "วิศวกรรมปัญญาประดิษฐ์"]
        
        print("=== Starting TCAS Engineering Programs Scraper ===")
        
        search_results = self.search_engineering_programs(keywords)
        if not search_results:
            print("No programs found")
            return []
        
        print(f"Processing {len(search_results)} programs")
        
        for i, result in enumerate(search_results, 1):
            print(f"[{i}/{len(search_results)}] {result['title']}")
            
            processing_info, main_data = self.extract_course_info(result['url'])
            
            if processing_info:
                # Add metadata
                processing_info.update({
                    'ลำดับ': i,
                    'คำค้นหา': result['keyword'],
                    'ข้อมูลเริ่มต้น': result['title']
                })
                self.processing_data.append(processing_info)
                
                print(f"  University: {processing_info['มหาวิทยาลัย']}")
                print(f"  Course: {processing_info['หลักสูตร']}")
                print(f"  Type: {processing_info['ประเภทหลักสูตร']}")
                print(f"  Cost: {processing_info['ค่าใช้จ่าย']}")
            
        return self.data
    
    def save_to_excel(self, filename="tcas_engineering_programs.xlsx"):
        """Save data to Excel with error handling"""
        if not self.data and not self.processing_data:
            print("No data to save")
            return None
        
        # Handle file conflicts
        if os.path.exists(filename):
            try:
                with open(filename, 'r'):
                    pass
            except PermissionError:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"tcas_engineering_programs_{timestamp}.xlsx"
                print(f"File in use. Saving to: {filename}")
        
        try:
            with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                if self.processing_data:
                    pd.DataFrame(self.processing_data).to_excel(writer, sheet_name='Processing_Data', index=False)
                    print(f"Processing data saved: {len(self.processing_data)} records")
                
                if self.data:
                    df = pd.DataFrame(self.data).sort_values('ค่าเทอม_บาท')
                    # Reorder columns
                    column_order = ['ลำดับ', 'คำค้นหา', 'มหาวิทยาลัย', 'หลักสูตร', 'ประเภทหลักสูตร', 'ค่าใช้จ่าย', 'URL', 'ข้อมูลเริ่มต้น']
                    if all(col in df.columns for col in column_order):
                        df = df[column_order]
                    df.to_excel(writer, sheet_name='Main_Data', index=False)
                    
                    print(f"Main data saved: {len(df)} records")
                    print(f"Fee range: {df['ค่าเทอม_บาท'].min():,} - {df['ค่าเทอม_บาท'].max():,} บาท/เทอม")
                    print(f"Average: {df['ค่าเทอม_บาท'].mean():,.0f} บาท/เทอม")
                    
                    return df
                else:
                    return pd.DataFrame(self.processing_data)
                    
        except Exception as e:
            print(f"Save failed: {e}")
            return None
    
    def close(self):
        """Close the webdriver"""
        if self.driver:
            self.driver.quit()
            print("Browser closed")

def main():
    """Main function"""
    scraper = TCASEngineeringScraper()
    
    if not scraper.driver:
        print("Failed to initialize driver")
        return
    
    try:
        scraper.scrape_engineering_programs()
        df = scraper.save_to_excel()
        
        if df is not None and len(df) > 0:
            print("\n=== Sample Data ===")
            display_cols = ['มหาวิทยาลัย', 'หลักสูตร', 'ค่าเทอม_บาท'] if 'ค่าเทอม_บาท' in df.columns else df.columns[:3]
            print(df[display_cols].head())
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        scraper.close()

if __name__ == "__main__":
    main()