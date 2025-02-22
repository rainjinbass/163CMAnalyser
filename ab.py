import re
import requests
from bs4 import BeautifulSoup

def get_album_song_ids(album_url):
    # 从URL中提取专辑ID
    album_id_match = re.search(r'id=(\d+)', album_url)
    if not album_id_match:
        raise ValueError("Invalid album URL")
    album_id = album_id_match.group(1)
    
    # 构造网易云音乐专辑页面的URL（注意：这个URL可能会变化，需要根据实际情况调整）
    album_page_url = f'https://music.163.com/#/album?id={album_id}'
    
    # 发送HTTP请求获取页面内容
    # 注意：由于网易云音乐使用了前端框架，直接请求可能无法获取完整数据，这里假设可以直接获取
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    response = requests.get(album_page_url, headers=headers)
    response.raise_for_status()  # 检查请求是否成功
    
    # 解析HTML内容
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # 查找歌曲ID（注意：这个选择器可能会变化，需要根据实际情况调整）
    # 网易云音乐的页面结构可能会变化，这里假设歌曲ID在某个特定的HTML标签中
    # 例如，假设歌曲ID在形如 <a href="/song?id=1234567"> 的链接中
    song_id_pattern = re.compile(r'/song\?id=(\d+)')
    song_ids = [match.group(1) for match in song_id_pattern.finditer(str(soup))]
    
    return song_ids

def main():
    # 用户输入专辑URL
    album_url = input("请输入专辑URL（如 https://music.163.com/#/album?id=34167）：")
    
    try:
        song_ids = get_album_song_ids(album_url)
        
        # 将歌曲ID写入stack.txt文件
        with open('stack.txt', 'w') as file:
            for song_id in song_ids:
                file.write(song_id + '\n')
        
        print("歌曲ID已写入stack.txt文件")
    except Exception as e:
        print(f"发生错误：{e}")

if __name__ == "__main__":
    main()
