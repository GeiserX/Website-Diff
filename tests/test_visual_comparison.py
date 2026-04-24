"""Tests for visual comparison module."""

import os
import io
import pytest
import tempfile
from unittest.mock import patch, Mock, MagicMock, PropertyMock
from pathlib import Path
from PIL import Image

from wayback_diff.visual_comparison import (
    VisualComparison,
    SELENIUM_AVAILABLE,
    WEBDRIVER_MANAGER_AVAILABLE,
)


class TestVisualComparisonInit:
    """Test VisualComparison initialization."""

    def test_init_defaults(self):
        """Test default initialization."""
        vc = VisualComparison()
        assert vc.browser_name == 'chrome'
        assert vc.headless is True
        assert vc.viewport_width == 1920
        assert vc.viewport_height == 1080
        assert vc.wait_time == 3
        assert vc.driver is None

    def test_init_custom(self):
        """Test custom initialization."""
        vc = VisualComparison(
            browser='firefox',
            headless=False,
            viewport_width=1280,
            viewport_height=720,
            wait_time=5
        )
        assert vc.browser_name == 'firefox'
        assert vc.headless is False
        assert vc.viewport_width == 1280
        assert vc.viewport_height == 720
        assert vc.wait_time == 5

    def test_init_all_supported_browsers(self):
        """Test initialization with all supported browser names."""
        for browser in ['chrome', 'chromium', 'firefox', 'opera', 'edge']:
            vc = VisualComparison(browser=browser)
            assert vc.browser_name == browser

    def test_init_invalid_browser(self):
        """Test initialization with invalid browser."""
        with pytest.raises(ValueError, match="Browser must be one of"):
            VisualComparison(browser='safari')

    def test_init_case_insensitive_browser(self):
        """Test browser name is lowercased."""
        vc = VisualComparison(browser='Chrome')
        assert vc.browser_name == 'chrome'

    @patch('wayback_diff.visual_comparison.SELENIUM_AVAILABLE', False)
    def test_init_no_selenium(self):
        """Test initialization when selenium is not available."""
        with pytest.raises(ImportError, match="Selenium is required"):
            VisualComparison()

    def test_supported_browsers_list(self):
        """Test supported browsers class variable."""
        assert 'chrome' in VisualComparison.SUPPORTED_BROWSERS
        assert 'firefox' in VisualComparison.SUPPORTED_BROWSERS
        assert 'chromium' in VisualComparison.SUPPORTED_BROWSERS

    def test_default_viewport_constants(self):
        """Test default viewport constants."""
        assert VisualComparison.DEFAULT_VIEWPORT_WIDTH == 1920
        assert VisualComparison.DEFAULT_VIEWPORT_HEIGHT == 1080


class TestDetectAvailableBrowsers:
    """Test browser detection."""

    @patch('wayback_diff.visual_comparison.SELENIUM_AVAILABLE', False)
    def test_detect_no_selenium(self):
        """Test detection when selenium unavailable."""
        result = VisualComparison.detect_available_browsers()
        assert result == []

    @patch('wayback_diff.visual_comparison.SELENIUM_AVAILABLE', True)
    @patch('wayback_diff.visual_comparison.webdriver')
    def test_detect_chrome_available(self, mock_webdriver):
        """Test detection when Chrome is available."""
        mock_driver = Mock()
        mock_webdriver.Chrome.return_value = mock_driver

        result = VisualComparison.detect_available_browsers()
        assert 'chrome' in result

    @patch('wayback_diff.visual_comparison.SELENIUM_AVAILABLE', True)
    @patch('wayback_diff.visual_comparison.webdriver')
    def test_detect_all_fail_returns_chrome(self, mock_webdriver):
        """Test fallback to chrome when no browsers detected."""
        mock_webdriver.Chrome.side_effect = Exception("No chrome")
        mock_webdriver.Firefox.side_effect = Exception("No firefox")
        mock_webdriver.Edge.side_effect = Exception("No edge")

        result = VisualComparison.detect_available_browsers()
        assert result == ['chrome']


class TestCompareImages:
    """Test image comparison."""

    def _create_test_image(self, width=100, height=100, color=(255, 0, 0)):
        """Create a test image."""
        img = Image.new('RGB', (width, height), color=color)
        return img

    def _save_test_image(self, path, width=100, height=100, color=(255, 0, 0)):
        """Save a test image to path."""
        img = self._create_test_image(width, height, color)
        img.save(path)
        return path

    def test_compare_identical_images(self):
        """Test comparing identical images."""
        with tempfile.TemporaryDirectory() as tmpdir:
            img_path = os.path.join(tmpdir, "img.png")
            self._save_test_image(img_path, color=(100, 100, 100))

            vc = VisualComparison()
            result = vc.compare_images(img_path, img_path)

            assert float(result['difference_ratio']) == 0.0
            assert int(result['different_pixels']) == 0
            assert result['is_similar'] == True

    def test_compare_different_images(self):
        """Test comparing different images."""
        with tempfile.TemporaryDirectory() as tmpdir:
            img1_path = os.path.join(tmpdir, "img1.png")
            img2_path = os.path.join(tmpdir, "img2.png")
            self._save_test_image(img1_path, color=(255, 0, 0))
            self._save_test_image(img2_path, color=(0, 0, 255))

            vc = VisualComparison()
            result = vc.compare_images(img1_path, img2_path)

            assert result['difference_ratio'] > 0
            assert result['different_pixels'] > 0

    def test_compare_images_different_sizes(self):
        """Test comparing images of different sizes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            img1_path = os.path.join(tmpdir, "img1.png")
            img2_path = os.path.join(tmpdir, "img2.png")
            self._save_test_image(img1_path, width=100, height=100)
            self._save_test_image(img2_path, width=200, height=200)

            vc = VisualComparison()
            result = vc.compare_images(img1_path, img2_path)

            assert 'difference_ratio' in result
            assert result['total_pixels'] > 0

    def test_compare_images_output_path(self):
        """Test that comparison image is saved."""
        with tempfile.TemporaryDirectory() as tmpdir:
            img1_path = os.path.join(tmpdir, "img1.png")
            img2_path = os.path.join(tmpdir, "img2.png")
            output_path = os.path.join(tmpdir, "comparison.png")
            self._save_test_image(img1_path, color=(255, 0, 0))
            self._save_test_image(img2_path, color=(0, 255, 0))

            vc = VisualComparison()
            result = vc.compare_images(img1_path, img2_path, output_path=output_path)

            assert os.path.exists(output_path)
            assert result['comparison_image_path'] == output_path

    def test_compare_images_no_output_path(self):
        """Test comparison without saving."""
        with tempfile.TemporaryDirectory() as tmpdir:
            img1_path = os.path.join(tmpdir, "img1.png")
            img2_path = os.path.join(tmpdir, "img2.png")
            self._save_test_image(img1_path)
            self._save_test_image(img2_path)

            vc = VisualComparison()
            result = vc.compare_images(img1_path, img2_path)

            assert result['comparison_image_path'] is None

    def test_compare_images_rgba(self):
        """Test comparing RGBA images (converted to RGB)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            img1_path = os.path.join(tmpdir, "img1.png")
            img2_path = os.path.join(tmpdir, "img2.png")

            img1 = Image.new('RGBA', (50, 50), (255, 0, 0, 128))
            img1.save(img1_path)
            img2 = Image.new('RGBA', (50, 50), (0, 0, 255, 128))
            img2.save(img2_path)

            vc = VisualComparison()
            result = vc.compare_images(img1_path, img2_path)

            assert 'difference_ratio' in result

    def test_compare_images_threshold(self):
        """Test custom threshold parameter."""
        with tempfile.TemporaryDirectory() as tmpdir:
            img1_path = os.path.join(tmpdir, "img1.png")
            img2_path = os.path.join(tmpdir, "img2.png")
            # Clearly different colors
            self._save_test_image(img1_path, color=(0, 0, 0))
            self._save_test_image(img2_path, color=(255, 255, 255))

            vc = VisualComparison()
            # With very high threshold, even big differences are "similar"
            result_high = vc.compare_images(img1_path, img2_path, threshold=1.0)
            assert result_high['is_similar'] == True

            # With low threshold, should be different
            result_low = vc.compare_images(img1_path, img2_path, threshold=0.1)
            assert int(result_low['different_pixels']) > 0


class TestCompareImagesWithoutNumpy:
    """Test image comparison fallback without numpy."""

    def _save_test_image(self, path, width=20, height=20, color=(255, 0, 0)):
        """Save a small test image."""
        img = Image.new('RGB', (width, height), color=color)
        img.save(path)

    def test_compare_fallback_identical(self):
        """Test pixel-by-pixel fallback with identical images."""
        with tempfile.TemporaryDirectory() as tmpdir:
            img_path = os.path.join(tmpdir, "img.png")
            self._save_test_image(img_path, width=10, height=10, color=(100, 100, 100))

            vc = VisualComparison()

            # Force the ImportError fallback path by making np.array raise
            import numpy as np
            with patch.object(np, 'array', side_effect=ImportError("no numpy")):
                result = vc.compare_images(img_path, img_path)

            assert float(result['difference_ratio']) == 0.0
            assert int(result['different_pixels']) == 0

    def test_compare_fallback_different(self):
        """Test pixel-by-pixel fallback with different images."""
        with tempfile.TemporaryDirectory() as tmpdir:
            img1_path = os.path.join(tmpdir, "img1.png")
            img2_path = os.path.join(tmpdir, "img2.png")
            self._save_test_image(img1_path, width=10, height=10, color=(255, 0, 0))
            self._save_test_image(img2_path, width=10, height=10, color=(0, 0, 255))

            vc = VisualComparison()

            import numpy as np
            with patch.object(np, 'array', side_effect=ImportError("no numpy")):
                result = vc.compare_images(img1_path, img2_path)

            assert float(result['difference_ratio']) > 0
            assert int(result['different_pixels']) > 0

    def test_compare_fallback_with_output(self):
        """Test pixel-by-pixel fallback saves comparison output."""
        with tempfile.TemporaryDirectory() as tmpdir:
            img1_path = os.path.join(tmpdir, "img1.png")
            img2_path = os.path.join(tmpdir, "img2.png")
            out_path = os.path.join(tmpdir, "comp.png")
            self._save_test_image(img1_path, width=5, height=5, color=(100, 100, 100))
            self._save_test_image(img2_path, width=5, height=5, color=(110, 110, 110))

            vc = VisualComparison()

            import numpy as np
            with patch.object(np, 'array', side_effect=ImportError("no numpy")):
                result = vc.compare_images(img1_path, img2_path, output_path=out_path)

            assert os.path.exists(out_path)


class TestCreateSideBySide:
    """Test side-by-side comparison image creation."""

    def test_create_side_by_side(self):
        """Test creating side-by-side image."""
        vc = VisualComparison()
        img1 = Image.new('RGB', (100, 100), color=(255, 0, 0))
        img2 = Image.new('RGB', (100, 100), color=(0, 255, 0))
        diff = Image.new('RGB', (100, 100), color=(0, 0, 255))

        result = vc._create_side_by_side(img1, img2, diff)

        assert isinstance(result, Image.Image)
        # Width should be 3 images + spacing
        assert result.width == 100 * 3 + 20
        # Height should include label
        assert result.height == 100 + 40


class TestQuit:
    """Test driver cleanup."""

    def test_quit_with_driver(self):
        """Test quitting with active driver."""
        vc = VisualComparison()
        mock_driver = Mock()
        vc.driver = mock_driver

        vc.quit()

        mock_driver.quit.assert_called_once()
        assert vc.driver is None

    def test_quit_without_driver(self):
        """Test quitting without driver does nothing."""
        vc = VisualComparison()
        vc.driver = None
        vc.quit()  # Should not raise

    def test_quit_driver_exception(self):
        """Test quitting when driver.quit raises exception."""
        vc = VisualComparison()
        mock_driver = Mock()
        mock_driver.quit.side_effect = Exception("Already closed")
        vc.driver = mock_driver

        vc.quit()  # Should not raise
        assert vc.driver is None


class TestContextManager:
    """Test context manager protocol."""

    def test_enter(self):
        """Test __enter__ returns self."""
        vc = VisualComparison()
        assert vc.__enter__() is vc

    def test_exit_calls_quit(self):
        """Test __exit__ calls quit."""
        vc = VisualComparison()
        mock_driver = Mock()
        vc.driver = mock_driver

        vc.__exit__(None, None, None)

        mock_driver.quit.assert_called_once()
        assert vc.driver is None

    def test_context_manager_usage(self):
        """Test using as context manager."""
        with VisualComparison() as vc:
            assert isinstance(vc, VisualComparison)
        assert vc.driver is None


class TestTakeScreenshot:
    """Test screenshot taking."""

    def test_take_screenshot_creates_driver(self):
        """Test that take_screenshot creates driver if needed."""
        vc = VisualComparison()
        assert vc.driver is None

        mock_driver = Mock()
        mock_driver.get_screenshot_as_png.return_value = b'\x89PNG'
        mock_driver.execute_script.side_effect = [
            'complete',  # document.readyState
            100,  # scrollWidth
            100,  # scrollHeight
            100,  # innerWidth
            100,  # innerHeight
            None,  # scrollTo
        ]

        with patch.object(vc, '_create_driver', return_value=mock_driver):
            # Mock full page screenshot
            with patch.object(vc, '_take_full_page_screenshot', return_value=b'\x89PNG'):
                result = vc.take_screenshot("https://example.com")

        assert result == b'\x89PNG'

    def test_take_screenshot_saves_to_file(self):
        """Test that screenshot is saved when output_path provided."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vc = VisualComparison()
            output_path = os.path.join(tmpdir, "screenshot.png")

            mock_driver = Mock()
            vc.driver = mock_driver
            mock_driver.execute_script.side_effect = [
                'complete',  # readyState
            ]

            with patch.object(vc, '_take_full_page_screenshot', return_value=b'\x89PNG\r\n\x1a\n'):
                result = vc.take_screenshot("https://example.com", output_path=output_path)

            assert os.path.exists(output_path)

    def test_take_screenshot_viewport_only(self):
        """Test viewport-only screenshot."""
        vc = VisualComparison()
        mock_driver = Mock()
        vc.driver = mock_driver
        mock_driver.get_screenshot_as_png.return_value = b'\x89PNG'
        mock_driver.execute_script.side_effect = [
            'complete',  # readyState
        ]

        result = vc.take_screenshot("https://example.com", full_page=False)
        assert result == b'\x89PNG'
        mock_driver.get_screenshot_as_png.assert_called_once()

    def test_take_screenshot_wayback_url(self):
        """Test that Wayback banner is removed for archive URLs."""
        vc = VisualComparison()
        mock_driver = Mock()
        vc.driver = mock_driver
        mock_driver.execute_script.side_effect = [
            'complete',  # readyState
            None,  # _remove_wayback_banner script
        ]

        with patch.object(vc, '_remove_wayback_banner'):
            with patch.object(vc, '_take_full_page_screenshot', return_value=b'\x89PNG'):
                result = vc.take_screenshot(
                    "https://web.archive.org/web/20230101/https://example.com/"
                )
                vc._remove_wayback_banner.assert_called_once()

    def test_take_screenshot_timeout_handled(self):
        """Test that WebDriverWait timeout is handled gracefully."""
        vc = VisualComparison()
        mock_driver = Mock()
        vc.driver = mock_driver

        # Simulate timeout on readyState check
        from selenium.common.exceptions import TimeoutException
        mock_driver.execute_script.side_effect = [
            TimeoutException("Timeout"),
        ]

        with patch.object(vc, '_take_full_page_screenshot', return_value=b'\x89PNG'):
            with patch('wayback_diff.visual_comparison.WebDriverWait') as mock_wait:
                mock_wait.return_value.until.side_effect = TimeoutException("Timeout")
                result = vc.take_screenshot("https://example.com")
                assert result == b'\x89PNG'


class TestCompareUrls:
    """Test multi-browser URL comparison."""

    def test_compare_urls_single_browser(self):
        """Test comparison with single browser."""
        vc = VisualComparison()

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create mock screenshots
            mock_screenshot = b'\x89PNG\r\n'

            with patch.object(vc, '_create_driver') as mock_create:
                mock_driver = Mock()
                mock_create.return_value = mock_driver

                with patch.object(vc, 'take_screenshot') as mock_ts:
                    mock_ts.return_value = mock_screenshot

                    with patch.object(vc, 'compare_images') as mock_ci:
                        mock_ci.return_value = {
                            'difference_ratio': 0.01,
                            'different_pixels': 100,
                            'total_pixels': 100000,
                            'is_similar': True,
                            'comparison_image_path': None,
                        }

                        results = vc.compare_urls(
                            "https://a.com", "https://b.com",
                            tmpdir, browsers=['chrome']
                        )

            assert 'chrome' in results
            assert results['chrome']['difference_ratio'] == 0.01

    def test_compare_urls_auto_detect(self):
        """Test comparison with auto-detected browsers."""
        vc = VisualComparison()

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(VisualComparison, 'detect_available_browsers',
                              return_value=['chrome']):
                with patch.object(vc, '_create_driver') as mock_create:
                    mock_driver = Mock()
                    mock_create.return_value = mock_driver

                    with patch.object(vc, 'take_screenshot', return_value=b'\x89PNG'):
                        with patch.object(vc, 'compare_images', return_value={
                            'difference_ratio': 0.0,
                            'different_pixels': 0,
                            'total_pixels': 100000,
                            'is_similar': True,
                            'comparison_image_path': None,
                        }):
                            results = vc.compare_urls(
                                "https://a.com", "https://b.com", tmpdir
                            )

            assert 'chrome' in results

    def test_compare_urls_browser_error(self):
        """Test comparison when screenshot raises error."""
        vc = VisualComparison()

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(vc, '_create_driver') as mock_create:
                mock_driver = Mock()
                mock_create.return_value = mock_driver

                with patch.object(vc, 'take_screenshot',
                                  side_effect=Exception("Screenshot failed")):
                    results = vc.compare_urls(
                        "https://a.com", "https://b.com",
                        tmpdir, browsers=['chrome']
                    )

            assert 'chrome' in results
            assert 'error' in results['chrome']

    def test_compare_urls_unsupported_browser_skipped(self):
        """Test that unsupported browsers are skipped."""
        vc = VisualComparison()

        with tempfile.TemporaryDirectory() as tmpdir:
            results = vc.compare_urls(
                "https://a.com", "https://b.com",
                tmpdir, browsers=['safari']
            )
            assert 'safari' not in results

    def test_compare_urls_creates_output_dir(self):
        """Test that output directory is created."""
        vc = VisualComparison()

        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = os.path.join(tmpdir, "screenshots")
            assert not os.path.exists(output_dir)

            with patch.object(vc, '_create_driver') as mock_create:
                mock_driver = Mock()
                mock_create.return_value = mock_driver

                with patch.object(vc, 'take_screenshot', return_value=b'\x89PNG'):
                    with patch.object(vc, 'compare_images', return_value={
                        'difference_ratio': 0.0,
                        'different_pixels': 0,
                        'total_pixels': 100000,
                        'is_similar': True,
                        'comparison_image_path': None,
                    }):
                        vc.compare_urls(
                            "https://a.com", "https://b.com",
                            output_dir, browsers=['chrome']
                        )

            assert os.path.exists(output_dir)


class TestRemoveWaybackBanner:
    """Test Wayback banner removal."""

    def test_remove_banner(self):
        """Test that banner removal script is executed."""
        vc = VisualComparison()
        mock_driver = Mock()
        vc.driver = mock_driver

        with patch('wayback_diff.visual_comparison.time'):
            vc._remove_wayback_banner()

        mock_driver.execute_script.assert_called_once()
        script = mock_driver.execute_script.call_args[0][0]
        assert 'wm-ipp' in script

    def test_remove_banner_error_handled(self):
        """Test that banner removal errors are handled."""
        vc = VisualComparison()
        mock_driver = Mock()
        mock_driver.execute_script.side_effect = Exception("Script error")
        vc.driver = mock_driver

        # Should not raise
        vc._remove_wayback_banner()


class TestCreateDriver:
    """Test WebDriver creation."""

    @patch('wayback_diff.visual_comparison.WEBDRIVER_MANAGER_AVAILABLE', False)
    @patch('wayback_diff.visual_comparison.webdriver')
    def test_create_chrome_driver(self, mock_webdriver):
        """Test Chrome driver creation."""
        vc = VisualComparison(browser='chrome')
        mock_driver = Mock()
        mock_webdriver.Chrome.return_value = mock_driver

        result = vc._create_driver()
        assert result == mock_driver

    @patch('wayback_diff.visual_comparison.WEBDRIVER_MANAGER_AVAILABLE', False)
    @patch('wayback_diff.visual_comparison.webdriver')
    def test_create_firefox_driver(self, mock_webdriver):
        """Test Firefox driver creation."""
        vc = VisualComparison(browser='firefox')
        mock_driver = Mock()
        mock_webdriver.Firefox.return_value = mock_driver

        result = vc._create_driver()
        mock_driver.set_window_size.assert_called_once_with(1920, 1080)

    @patch('wayback_diff.visual_comparison.WEBDRIVER_MANAGER_AVAILABLE', True)
    @patch('wayback_diff.visual_comparison.ChromeDriverManager')
    @patch('wayback_diff.visual_comparison.webdriver')
    def test_create_chrome_with_manager(self, mock_webdriver, mock_manager):
        """Test Chrome driver creation with webdriver-manager."""
        vc = VisualComparison(browser='chrome')
        mock_driver = Mock()
        mock_webdriver.Chrome.return_value = mock_driver
        mock_manager.return_value.install.return_value = '/path/to/chromedriver'

        result = vc._create_driver()
        assert result == mock_driver

    @patch('wayback_diff.visual_comparison.WEBDRIVER_MANAGER_AVAILABLE', True)
    @patch('wayback_diff.visual_comparison.ChromeDriverManager')
    @patch('wayback_diff.visual_comparison.ChromeService')
    @patch('wayback_diff.visual_comparison.webdriver')
    def test_create_chrome_manager_fallback(self, mock_webdriver, mock_service,
                                            mock_manager):
        """Test Chrome driver falls back to system when manager fails."""
        vc = VisualComparison(browser='chrome')
        mock_driver = Mock()
        # Manager install fails, triggering fallback to system chromedriver
        mock_manager.return_value.install.side_effect = Exception("Download failed")
        mock_service.side_effect = Exception("Service failed")
        # First Chrome() call is the fallback (no service)
        mock_webdriver.Chrome.return_value = mock_driver

        result = vc._create_driver()
        assert result == mock_driver

    @patch('wayback_diff.visual_comparison.WEBDRIVER_MANAGER_AVAILABLE', False)
    @patch('wayback_diff.visual_comparison.webdriver')
    def test_create_chromium_driver(self, mock_webdriver):
        """Test Chromium driver creation."""
        vc = VisualComparison(browser='chromium')
        mock_driver = Mock()
        mock_webdriver.Chrome.return_value = mock_driver

        with patch('os.path.exists', return_value=False):
            result = vc._create_driver()
        assert result == mock_driver

    @patch('wayback_diff.visual_comparison.WEBDRIVER_MANAGER_AVAILABLE', False)
    @patch('wayback_diff.visual_comparison.webdriver')
    def test_create_opera_driver(self, mock_webdriver):
        """Test Opera driver creation."""
        vc = VisualComparison(browser='opera')
        mock_driver = Mock()
        mock_webdriver.Chrome.return_value = mock_driver

        with patch('os.path.exists', return_value=False):
            result = vc._create_driver()
        assert result == mock_driver

    @patch('wayback_diff.visual_comparison.WEBDRIVER_MANAGER_AVAILABLE', False)
    @patch('wayback_diff.visual_comparison.webdriver')
    def test_create_edge_driver(self, mock_webdriver):
        """Test Edge driver creation."""
        vc = VisualComparison(browser='edge')
        mock_driver = Mock()
        mock_webdriver.Edge.return_value = mock_driver

        result = vc._create_driver()
        assert result == mock_driver

    @patch('wayback_diff.visual_comparison.WEBDRIVER_MANAGER_AVAILABLE', False)
    @patch('wayback_diff.visual_comparison.webdriver')
    def test_create_chrome_headless_args(self, mock_webdriver):
        """Test Chrome headless arguments."""
        vc = VisualComparison(browser='chrome', headless=True)
        mock_driver = Mock()
        mock_webdriver.Chrome.return_value = mock_driver

        vc._create_driver()
        # Verify Chrome was called (args checked via options)
        mock_webdriver.Chrome.assert_called()

    @patch('wayback_diff.visual_comparison.WEBDRIVER_MANAGER_AVAILABLE', False)
    @patch('wayback_diff.visual_comparison.webdriver')
    def test_create_chrome_non_headless(self, mock_webdriver):
        """Test Chrome non-headless mode."""
        vc = VisualComparison(browser='chrome', headless=False)
        mock_driver = Mock()
        mock_webdriver.Chrome.return_value = mock_driver

        vc._create_driver()
        mock_webdriver.Chrome.assert_called()


class TestTakeFullPageScreenshot:
    """Test full page screenshot functionality."""

    def test_full_page_screenshot_basic(self):
        """Test full page screenshot with mocked driver."""
        vc = VisualComparison()
        mock_driver = Mock()
        vc.driver = mock_driver

        # Create a small test PNG
        img = Image.new('RGB', (100, 100), color=(255, 255, 255))
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')
        png_data = img_bytes.getvalue()

        mock_driver.current_url = "https://example.com"
        mock_driver.execute_script.side_effect = [
            100,   # scrollWidth
            100,   # scrollHeight
            100,   # innerWidth
            100,   # innerHeight
            None,  # scrollTo
            None,  # scrollTo(0,0) reset
        ]
        mock_driver.get_screenshot_as_png.return_value = png_data

        result = vc._take_full_page_screenshot()
        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_full_page_screenshot_wayback_url(self):
        """Test full page screenshot removes Wayback banner."""
        vc = VisualComparison()
        mock_driver = Mock()
        vc.driver = mock_driver

        img = Image.new('RGB', (50, 50), color=(200, 200, 200))
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')
        png_data = img_bytes.getvalue()

        mock_driver.current_url = "https://web.archive.org/web/20230101/https://example.com"
        # With _remove_wayback_banner patched out, execute_script calls are:
        # scrollWidth, scrollHeight, innerWidth, innerHeight, scrollTo, wayback-style, scrollTo-reset
        mock_driver.execute_script.side_effect = [
            50,    # scrollWidth
            50,    # scrollHeight
            50,    # innerWidth
            50,    # innerHeight
            None,  # scrollTo
            None,  # wayback style injection during scroll
            None,  # scrollTo(0,0) reset
        ]
        mock_driver.get_screenshot_as_png.return_value = png_data

        with patch.object(vc, '_remove_wayback_banner'):
            result = vc._take_full_page_screenshot()
            vc._remove_wayback_banner.assert_called_once()
        assert isinstance(result, bytes)

    def test_full_page_screenshot_multi_scroll(self):
        """Test full page screenshot that requires scrolling."""
        vc = VisualComparison()
        mock_driver = Mock()
        vc.driver = mock_driver

        # Page is 200x200 but viewport is 100x100, needs 4 screenshots
        img = Image.new('RGB', (100, 100), color=(128, 128, 128))
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')
        png_data = img_bytes.getvalue()

        mock_driver.current_url = "https://example.com"
        # Each scroll iteration calls execute_script for scrollTo
        mock_driver.execute_script.side_effect = [
            200,   # scrollWidth
            200,   # scrollHeight
            100,   # innerWidth
            100,   # innerHeight
            None,  # scrollTo(0,0)
            None,  # scrollTo(100,0)
            None,  # scrollTo(0,100)
            None,  # scrollTo(100,100)
            None,  # scrollTo(0,0) reset
        ]
        mock_driver.get_screenshot_as_png.return_value = png_data

        result = vc._take_full_page_screenshot()
        assert isinstance(result, bytes)
        # Should have taken 4 viewport screenshots
        assert mock_driver.get_screenshot_as_png.call_count == 4


class TestEdgeDriverFallback:
    """Test Edge driver creation with fallback paths."""

    @patch('wayback_diff.visual_comparison.WEBDRIVER_MANAGER_AVAILABLE', False)
    @patch('wayback_diff.visual_comparison.webdriver')
    def test_create_edge_fallback_to_chrome(self, mock_webdriver):
        """Test Edge driver falls back to Chrome-based Edge."""
        vc = VisualComparison(browser='edge')
        mock_driver = Mock()
        # Edge driver fails, Chrome-based Edge succeeds
        mock_webdriver.Edge.side_effect = Exception("No Edge driver")
        mock_webdriver.Chrome.return_value = mock_driver

        with patch('os.path.exists', return_value=False):
            result = vc._create_driver()
        assert result == mock_driver


class TestFirefoxDriverManager:
    """Test Firefox driver creation with webdriver-manager."""

    @patch('wayback_diff.visual_comparison.WEBDRIVER_MANAGER_AVAILABLE', True)
    @patch('wayback_diff.visual_comparison.GeckoDriverManager')
    @patch('wayback_diff.visual_comparison.FirefoxService')
    @patch('wayback_diff.visual_comparison.webdriver')
    def test_create_firefox_with_manager(self, mock_webdriver, mock_service,
                                          mock_manager):
        """Test Firefox driver creation with webdriver-manager."""
        vc = VisualComparison(browser='firefox')
        mock_driver = Mock()
        mock_webdriver.Firefox.return_value = mock_driver
        mock_manager.return_value.install.return_value = '/path/to/geckodriver'

        result = vc._create_driver()
        mock_driver.set_window_size.assert_called_once()

    @patch('wayback_diff.visual_comparison.WEBDRIVER_MANAGER_AVAILABLE', True)
    @patch('wayback_diff.visual_comparison.GeckoDriverManager')
    @patch('wayback_diff.visual_comparison.FirefoxService')
    @patch('wayback_diff.visual_comparison.webdriver')
    def test_create_firefox_manager_fallback(self, mock_webdriver, mock_service,
                                              mock_manager):
        """Test Firefox driver falls back when manager fails."""
        vc = VisualComparison(browser='firefox')
        mock_driver = Mock()
        mock_manager.return_value.install.side_effect = Exception("Download failed")
        mock_service.side_effect = Exception("Service failed")
        mock_webdriver.Firefox.return_value = mock_driver

        result = vc._create_driver()
        assert result == mock_driver


class TestModuleEntryPoint:
    """Test __main__.py module entry point."""

    def test_main_module_import(self):
        """Test that __main__ module can be imported."""
        import wayback_diff.__main__

    def test_package_version(self):
        """Test package version is set."""
        from wayback_diff import __version__
        assert __version__ == "1.1.0"
