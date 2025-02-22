import re
import requests
import os

def extract_album_id(url):
    """从网易云专辑URL中提取专辑ID"""
    match = re.search(r'id=(\d+)(?:&|$)', url)
    if not match:
        raise ValueError(f"无效的专辑URL格式: {url}")
    return match.group(1)

def get_album_data(album_id):
    """通过网易云API获取专辑数据"""
    api_url = f"https://music.163.com/api/album/{album_id}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Referer": "https://music.163.com/"
    }
    
    response = requests.get(api_url, headers=headers)
    response.raise_for_status()
    return response.json()

def process_album(url):
    """处理单个专辑URL"""
    try:
        # 提取专辑ID
        album_id = extract_album_id(url)
        
        # 获取专辑数据
        data = get_album_data(album_id)
        
        # 提取歌曲ID
        songs = data["album"]["songs"]
        return [str(song["id"]) for song in songs]
    except Exception as e:
        print(f"处理专辑失败 ({url}): {str(e)}")
        return None

def update_temp_file(song_ids):
    """将歌曲ID追加到temp.txt"""
    with open("temp.txt", "a", encoding="utf-8") as f:
        f.write("\n".join(song_ids) + "\n")

def main():
    # 确保ready.txt存在
    if not os.path.exists("ready.txt"):
        print("ready.txt 文件不存在")
        return

    # 读取待处理专辑列表
    with open("ready.txt", "r+", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]
        f.seek(0)
        f.truncate()
        
        processed_count = 0
        
        for url in lines:
            # 处理专辑
            song_ids = process_album(url)
            
            if song_ids:
                # 写入temp.txt
                update_temp_file(song_ids)
                
                # 显示处理信息
                print(f"成功处理专辑: {url}")
                print(f"提取到 {len(song_ids)} 首歌曲ID")
                processed_count += 1
            else:
                # 保留处理失败的行
                f.write(url + "\n")
        
        print(f"处理完成，共成功处理 {processed_count} 个专辑")

if __name__ == "__main__":
    main()
