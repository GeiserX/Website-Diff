"""Visual comparison module for taking screenshots and comparing them."""

import os
import time
from typing import Optional, Tuple, List, Dict
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import io

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options as ChromeOptions
    from selenium.webdriver.chrome.service import Service as ChromeService
    from selenium.webdriver.firefox.options import Options as FirefoxOptions
    from selenium.webdriver.firefox.service import Service as FirefoxService
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, WebDriverException
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

try:
    from webdriver_manager.chrome import ChromeDriverManager
    from webdriver_manager.firefox import GeckoDriverManager
    WEBDRIVER_MANAGER_AVAILABLE = True
except ImportError:
    WEBDRIVER_MANAGER_AVAILABLE = False


class VisualComparison:
    """Take screenshots and compare web pages visually."""
    
    SUPPORTED_BROWSERS = ['chrome', 'firefox']
    DEFAULT_VIEWPORT_WIDTH = 1920
    DEFAULT_VIEWPORT_HEIGHT = 1080
    
    def __init__(self, browser: str = 'chrome', headless: bool = True, 
                 viewport_width: int = None, viewport_height: int = None,
                 wait_time: int = 3):
        """Initialize visual comparison.
        
        Args:
            browser: Browser to use ('chrome' or 'firefox')
            headless: Run browser in headless mode
            viewport_width: Browser viewport width in pixels
            viewport_height: Browser viewport height in pixels
            wait_time: Time to wait for page to load (seconds)
        """
        if not SELENIUM_AVAILABLE:
            raise ImportError(
                "Selenium is required for visual comparison. "
                "Install with: pip install selenium"
            )
        
        if browser.lower() not in self.SUPPORTED_BROWSERS:
            raise ValueError(f"Browser must be one of {self.SUPPORTED_BROWSERS}")
        
        self.browser_name = browser.lower()
        self.headless = headless
        self.viewport_width = viewport_width or self.DEFAULT_VIEWPORT_WIDTH
        self.viewport_height = viewport_height or self.DEFAULT_VIEWPORT_HEIGHT
        self.wait_time = wait_time
        self.driver = None
    
    def _create_driver(self) -> webdriver.Remote:
        """Create and configure WebDriver."""
        if self.browser_name == 'chrome':
            options = ChromeOptions()
            if self.headless:
                options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument(f'--window-size={self.viewport_width},{self.viewport_height}')
            options.add_argument('--disable-gpu')
            options.add_argument('--disable-extensions')
            
            # Try to use webdriver-manager if available
            if WEBDRIVER_MANAGER_AVAILABLE:
                try:
                    service = ChromeService(ChromeDriverManager().install())
                    driver = webdriver.Chrome(service=service, options=options)
                except Exception:
                    # Fallback to system chromedriver
                    driver = webdriver.Chrome(options=options)
            else:
                driver = webdriver.Chrome(options=options)
        
        elif self.browser_name == 'firefox':
            options = FirefoxOptions()
            if self.headless:
                options.add_argument('--headless')
            options.set_preference("general.useragent.override", 
                                  "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
            
            # Try to use webdriver-manager if available
            if WEBDRIVER_MANAGER_AVAILABLE:
                try:
                    service = FirefoxService(GeckoDriverManager().install())
                    driver = webdriver.Firefox(service=service, options=options)
                except Exception:
                    # Fallback to system geckodriver
                    driver = webdriver.Firefox(options=options)
            else:
                driver = webdriver.Firefox(options=options)
            
            driver.set_window_size(self.viewport_width, self.viewport_height)
        
        return driver
    
    def take_screenshot(self, url: str, output_path: Optional[str] = None,
                        full_page: bool = True) -> bytes:
        """Take a screenshot of a web page.
        
        Args:
            url: URL to screenshot
            output_path: Optional path to save screenshot
            full_page: Take full page screenshot (scroll and stitch)
            
        Returns:
            Screenshot as bytes
        """
        if not self.driver:
            self.driver = self._create_driver()
        
        try:
            # Navigate to URL
            self.driver.get(url)
            
            # Wait for page to load
            time.sleep(self.wait_time)
            
            # Wait for document ready state
            try:
                WebDriverWait(self.driver, 10).until(
                    lambda d: d.execute_script('return document.readyState') == 'complete'
                )
            except TimeoutException:
                pass  # Continue anyway
            
            if full_page:
                # Full page screenshot using JavaScript
                screenshot = self._take_full_page_screenshot()
            else:
                # Viewport screenshot
                screenshot = self.driver.get_screenshot_as_png()
            
            # Save if output path provided
            if output_path:
                Path(output_path).parent.mkdir(parents=True, exist_ok=True)
                with open(output_path, 'wb') as f:
                    f.write(screenshot)
            
            return screenshot
            
        except WebDriverException as e:
            raise Exception(f"Failed to take screenshot: {e}")
    
    def _take_full_page_screenshot(self) -> bytes:
        """Take full page screenshot by scrolling and stitching."""
        # Get page dimensions
        total_width = self.driver.execute_script("return document.body.scrollWidth")
        total_height = self.driver.execute_script("return document.body.scrollHeight")
        viewport_width = self.driver.execute_script("return window.innerWidth")
        viewport_height = self.driver.execute_script("return window.innerHeight")
        
        # Create a blank image with the full page size
        screenshot = Image.new('RGB', (total_width, total_height), color='white')
        
        # Scroll and capture
        scroll_x = 0
        scroll_y = 0
        
        while scroll_y < total_height:
            while scroll_x < total_width:
                # Scroll to position
                self.driver.execute_script(f"window.scrollTo({scroll_x}, {scroll_y});")
                time.sleep(0.2)  # Small delay for scroll
                
                # Capture viewport
                viewport_screenshot = self.driver.get_screenshot_as_png()
                viewport_img = Image.open(io.BytesIO(viewport_screenshot))
                
                # Calculate paste position
                paste_x = scroll_x
                paste_y = scroll_y
                
                # Handle edge cases where viewport might be smaller
                crop_width = min(viewport_width, total_width - scroll_x)
                crop_height = min(viewport_height, total_height - scroll_y)
                
                # Crop and paste
                if crop_width > 0 and crop_height > 0:
                    cropped = viewport_img.crop((0, 0, crop_width, crop_height))
                    screenshot.paste(cropped, (paste_x, paste_y))
                
                scroll_x += viewport_width
                
                if scroll_x >= total_width:
                    break
            
            scroll_x = 0
            scroll_y += viewport_height
            
            if scroll_y >= total_height:
                break
        
        # Reset scroll position
        self.driver.execute_script("window.scrollTo(0, 0);")
        
        # Convert to bytes
        img_bytes = io.BytesIO()
        screenshot.save(img_bytes, format='PNG')
        return img_bytes.getvalue()
    
    def compare_images(self, image1_path: str, image2_path: str,
                      output_path: Optional[str] = None,
                      threshold: float = 0.1) -> Dict:
        """Compare two images and generate diff.
        
        Args:
            image1_path: Path to first image
            image2_path: Path to second image
            output_path: Path to save comparison image
            threshold: Difference threshold (0.0-1.0)
            
        Returns:
            Dictionary with comparison results
        """
        # Load images
        img1 = Image.open(image1_path)
        img2 = Image.open(image2_path)
        
        # Resize if dimensions differ
        if img1.size != img2.size:
            # Resize to common size (use larger dimensions)
            max_width = max(img1.width, img2.width)
            max_height = max(img1.height, img2.height)
            img1 = img1.resize((max_width, max_height), Image.Resampling.LANCZOS)
            img2 = img2.resize((max_width, max_height), Image.Resampling.LANCZOS)
        
        # Convert to RGB if needed
        if img1.mode != 'RGB':
            img1 = img1.convert('RGB')
        if img2.mode != 'RGB':
            img2 = img2.convert('RGB')
        
        # Calculate difference
        diff_img = Image.new('RGB', img1.size)
        diff_pixels = 0
        total_pixels = img1.width * img1.height
        
        for x in range(img1.width):
            for y in range(img1.height):
                pixel1 = img1.getpixel((x, y))
                pixel2 = img2.getpixel((x, y))
                
                # Calculate pixel difference
                diff = sum(abs(p1 - p2) for p1, p2 in zip(pixel1, pixel2)) / (3 * 255)
                
                if diff > threshold:
                    # Highlight difference in red
                    diff_img.putpixel((x, y), (255, 0, 0))
                    diff_pixels += 1
                else:
                    # Use average of both pixels
                    avg = tuple((p1 + p2) // 2 for p1, p2 in zip(pixel1, pixel2))
                    diff_img.putpixel((x, y), avg)
        
        difference_ratio = diff_pixels / total_pixels
        
        # Create side-by-side comparison
        comparison = self._create_side_by_side(img1, img2, diff_img)
        
        # Save comparison image
        if output_path:
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            comparison.save(output_path)
        
        return {
            'difference_ratio': difference_ratio,
            'different_pixels': diff_pixels,
            'total_pixels': total_pixels,
            'is_similar': difference_ratio <= threshold,
            'comparison_image_path': output_path
        }
    
    def _create_side_by_side(self, img1: Image.Image, img2: Image.Image,
                             diff_img: Image.Image) -> Image.Image:
        """Create side-by-side comparison image."""
        # Add labels
        label_height = 40
        width = img1.width * 3 + 20  # 3 images + spacing
        height = img1.height + label_height
        
        comparison = Image.new('RGB', (width, height), color='white')
        draw = ImageDraw.Draw(comparison)
        
        try:
            # Try to use a nice font
            font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 20)
        except:
            try:
                font = ImageFont.truetype("arial.ttf", 20)
            except:
                font = ImageFont.load_default()
        
        # Paste images
        comparison.paste(img1, (0, label_height))
        comparison.paste(img2, (img1.width + 10, label_height))
        comparison.paste(diff_img, (img1.width * 2 + 20, label_height))
        
        # Add labels
        draw.text((img1.width // 2 - 50, 10), "Original", fill='black', font=font)
        draw.text((img1.width + 10 + img1.width // 2 - 50, 10), "New", fill='black', font=font)
        draw.text((img1.width * 2 + 20 + img1.width // 2 - 50, 10), "Diff", fill='red', font=font)
        
        return comparison
    
    def compare_urls(self, url1: str, url2: str, output_dir: str,
                     browsers: Optional[List[str]] = None) -> Dict:
        """Compare two URLs visually across multiple browsers.
        
        Args:
            url1: First URL
            url2: Second URL
            output_dir: Directory to save screenshots and comparisons
            browsers: List of browsers to test (default: ['chrome'])
            
        Returns:
            Dictionary with comparison results for each browser
        """
        if browsers is None:
            browsers = ['chrome']
        
        results = {}
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        for browser_name in browsers:
            if browser_name not in self.SUPPORTED_BROWSERS:
                continue
            
            # Create new instance for each browser
            self.browser_name = browser_name
            if self.driver:
                self.quit()
            self.driver = self._create_driver()
            
            try:
                # Take screenshots
                screenshot1_path = output_path / f"{browser_name}_url1.png"
                screenshot2_path = output_path / f"{browser_name}_url2.png"
                
                print(f"Taking screenshot of {url1} with {browser_name}...")
                self.take_screenshot(url1, str(screenshot1_path))
                
                print(f"Taking screenshot of {url2} with {browser_name}...")
                self.take_screenshot(url2, str(screenshot2_path))
                
                # Compare
                comparison_path = output_path / f"{browser_name}_comparison.png"
                comparison_result = self.compare_images(
                    str(screenshot1_path),
                    str(screenshot2_path),
                    str(comparison_path)
                )
                
                results[browser_name] = {
                    'screenshot1': str(screenshot1_path),
                    'screenshot2': str(screenshot2_path),
                    'comparison': str(comparison_path),
                    **comparison_result
                }
                
            except Exception as e:
                results[browser_name] = {
                    'error': str(e)
                }
            finally:
                self.quit()
        
        return results
    
    def quit(self):
        """Close the browser driver."""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
            self.driver = None
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.quit()
