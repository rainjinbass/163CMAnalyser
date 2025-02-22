import os
import re
import time
import json
import random
import requests
import logging
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from mutagen.flac import FLAC, Picture
from mutagen.id3 import ID3, APIC, TIT2, TALB, TPE1, TRCK
from mutagen.id3._util import ID3NoHeaderError

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('downloader.log'),
        logging.StreamHandler()
    ]
)

class NeteaseDownloader:
    def __init__(self):
        self.session = requests.Session()
        self.cookies = {}
        self.driver = None
        self.chrome_options = self._init_chrome_options()
        self._prepare_environment()

    def _init_chrome_options(self):
        """初始化浏览器选项"""
        options = Options()
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--headless")  # 无头模式
        options.add_argument(f"user-agent={self._random_ua()}")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        return options

    def _random_ua(self):
        """生成随机User-Agent"""
        chrome_versions = [
            '91.0.4472.124', '92.0.4515.107', '93.0.4577.63',
            '94.0.4606.61', '95.0.4638.54', '96.0.4664.45'
        ]
        return f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{random.choice(chrome_versions)} Safari/537.36"

    def _prepare_environment(self):
        """初始化环境"""
        Path('temp').mkdir(exist_ok=True)
        Path('result').mkdir(exist_ok=True)
        self._login()

    def _login(self):
        """通过浏览器获取有效Cookie"""
        try:
            # 使用webdriver-manager自动管理驱动
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(
                service=service,
                options=self.chrome_options
            )
            driver = webdriver.Chrome(options=self.chrome_options)
            driver.get("https://music.163.com")

            # 等待页面加载
            time.sleep(5)
            
            # 检查登录状态
            if "发现音乐" not in driver.page_source:
                self._manual_login(driver)

            # 获取Cookies
            self.cookies = {c['name']: c['value'] for c in driver.get_cookies()}
            logging.info("Cookie获取成功")

            # 关闭浏览器
            driver.quit()
        except Exception as e:
            logging.error(f"登录失败: {str(e)}")
            raise

    def _manual_login(self, driver):
        """处理需要手动登录的情况"""
        logging.warning("需要手动登录！")
        driver.execute_script("document.querySelector('.link').click()")
        input("请手动完成登录后按回车继续...")
        time.sleep(5)  # 等待登录完成

    def _get_signed_url(self, song_id):
        """获取带签名的真实下载地址"""
        api_url = "https://music.163.com/api/song/enhance/player/url"
        params = {
            "id": song_id,
            "br": 999000,  # 音质参数
            "csrf_token": self.cookies.get('__csrf', '')
        }

        headers = {
            "User-Agent": self._random_ua(),
            "Referer": "https://music.163.com/",
            "X-Real-IP": f"{random.randint(100,255)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(0,255)}",
            "Cookie": "; ".join([f"{k}={v}" for k, v in self.cookies.items()])
        }

        try:
            response = self.session.get(
                api_url,
                params=params,
                headers=headers,
                timeout=30
            )
            data = response.json()
            if data['code'] == 200 and data['data'][0]['url']:
                return data['data'][0]['url']
            return None
        except Exception as e:
            logging.error(f"API请求失败: {str(e)}")
            return None

    def _download_file(self, url, save_path):
        """带反爬措施的下载函数"""
        headers = {
            "User-Agent": self._random_ua(),
            "Referer": "https://music.163.com/",
            "Origin": "https://music.163.com",
            "Accept-Encoding": "gzip, deflate, br",
            "Cookie": "; ".join([f"{k}={v}" for k, v in self.cookies.items()])
        }

        for attempt in range(3):
            try:
                response = self.session.get(
                    url,
                    headers=headers,
                    stream=True,
                    timeout=30
                )
                response.raise_for_status()

                # 验证内容类型
                content_type = response.headers.get('Content-Type', '')
                if 'audio' not in content_type and 'octet-stream' not in content_type:
                    raise ValueError(f"无效的音频类型: {content_type}")

                # 分块下载
                with open(save_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)

                # 验证文件大小
                if os.path.getsize(save_path) < 1024 * 100:  # 至少100KB
                    raise ValueError("文件大小异常")

                return True
            except Exception as e:
                logging.warning(f"下载失败（尝试{attempt+1}/3）: {str(e)}")
                time.sleep(2 ** attempt)  # 指数退避
                if attempt == 2:
                    return False

    def _process_metadata(self, file_path, metadata, cover_path):
        """处理元数据"""
        try:
            if file_path.suffix.lower() == '.flac':
                audio = FLAC(file_path)
                audio.update({
                    'title': metadata['title'],
                    'artist': metadata['artist'],
                    'album': metadata['album'],
                    'tracknumber': str(metadata['track_num'])
                })
                if cover_path.exists():
                    image = Picture()
                    image.type = 3
                    image.mime = 'image/jpeg'
                    image.data = cover_path.read_bytes()
                    audio.add_picture(image)
                audio.save()
            else:
                audio = ID3(file_path) if file_path.exists() else ID3()
                audio.add(TIT2(encoding=3, text=metadata['title']))
                audio.add(TPE1(encoding=3, text=metadata['artist']))
                audio.add(TALB(encoding=3, text=metadata['album']))
                audio.add(TRCK(encoding=3, text=str(metadata['track_num'])))
                if cover_path.exists():
                    audio.add(APIC(
                        encoding=0,
                        mime='image/jpeg',
                        type=3,
                        desc='Cover',
                        data=cover_path.read_bytes()
                    ))
                audio.save(file_path)
        except Exception as e:
            logging.error(f"元数据写入失败: {str(e)}")

    def process_album(self, album_dir):
        """处理单个专辑"""
        album_name = album_dir.name
        result_dir = Path('result') / album_name
        result_dir.mkdir(exist_ok=True)

        # 下载专辑封面
        cover_path = result_dir / 'cover.jpg'
        if not cover_path.exists():
            for temp_file in album_dir.glob('*.temp'):
                with open(temp_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                if match := re.search(r'歌曲图片:\s*(.+?)\n', content):
                    if self._download_file(match.group(1), cover_path):
                        break

        # 处理歌曲文件
        for temp_file in album_dir.glob('*.temp'):
            with open(temp_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # 提取元数据
            metadata = {
                'title': re.search(r'歌曲名称:\s*(.+?)\n', content).group(1),
                'artist': re.search(r'歌手:\s*(.+?)\n', content).group(1),
                'album': re.search(r'专辑名称:\s*(.+?)\n', content).group(1),
                'url': re.search(r'音乐链接:\s*(.+?)\n', content).group(1)
            }

            # 获取真实下载地址
            song_id = re.search(r'song\?id=(\d+)', metadata['url']).group(1)
            real_url = self._get_signed_url(song_id) or metadata['url']

            # 生成文件名
            track_num = int(temp_file.stem[:2])
            safe_title = re.sub(r'[\\/*?:"<>|]', '_', metadata['title'])
            file_ext = Path(real_url).suffix.split('?')[0]
            audio_path = result_dir / f"{track_num:02d} {safe_title}{file_ext}"

            # 下载音频
            if self._download_file(real_url, audio_path):
                # 处理元数据
                metadata['track_num'] = track_num
                self._process_metadata(audio_path, metadata, cover_path)

                # 移动歌词文件
                for lrc in album_dir.glob(f"{track_num:02d} *.lrc"):
                    shutil.move(lrc, result_dir / lrc.name)

                temp_file.unlink()

    def run(self):
        """主运行逻辑"""
        for album_dir in Path('temp').glob('*'):
            if album_dir.is_dir():
                try:
                    logging.info(f"开始处理专辑: {album_dir.name}")
                    self.process_album(album_dir)
                    # 清理空目录
                    try:
                        album_dir.rmdir()
                    except OSError:
                        pass
                except Exception as e:
                    logging.error(f"专辑处理失败 [{album_dir.name}]: {str(e)}")

if __name__ == '__main__':
    downloader = NeteaseDownloader()
    downloader.run()
