import os
import re
import subprocess
import sys
from pathlib import Path

def sanitize_filename(name):
    """清理非法文件名字符"""
    return re.sub(r'[\\/*?:"<>|]', '_', name).strip()

def parse_core_output(output):
    """解析core.py输出并提取关键信息"""
    patterns = {
        'album': r'专辑名称:\s*(.+?)\n',
        'song': r'歌曲名称:\s*(.+?)\n',
        'lyrics': r'歌词:\s*((?:\[.+\].+?\n)+)',
        'trans_lyrics': r'翻译歌词:\s*((?:\[.+\].+?\n)+)'
    }
    
    result = {}
    for key, pattern in patterns.items():
        match = re.search(pattern, output, re.DOTALL)
        if match:
            result[key] = match.group(1).strip()
    return result

def process_song(index, song_id):
    """处理单个歌曲ID"""
    cmd = [
        sys.executable,
        "core.py",
        "--mode", "gui",
        "--url", f"https://music.163.com/#/song?id={song_id}",
        "--level", "hires"
    ]
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
            timeout=30
        )
        output = result.stdout
    except Exception as e:
        output = f"Error processing {song_id}: {str(e)}"
    
    # 解析输出内容
    data = parse_core_output(output)
    if not data.get('album') or not data.get('song'):
        return False
    
    # 创建专辑目录
    album_dir = Path("temp") / sanitize_filename(data['album'])
    album_dir.mkdir(parents=True, exist_ok=True)
    
    # 生成带序号的文件名
    seq = f"{index:02d}"
    filename = f"{seq} {sanitize_filename(data['song'])}.temp"
    
    # 写入完整数据
    with open(album_dir / filename, "w", encoding="utf-8") as f:
        f.write(output)
    
    # 单独保存歌词文件
    if data.get('lyrics'):
        with open(album_dir / f"{seq} 歌词.lrc", "w", encoding="utf-8") as f:
            f.write(data['lyrics'])
    
    if data.get('trans_lyrics'):
        with open(album_dir / f"{seq} 翻译歌词.lrc", "w", encoding="utf-8") as f:
            f.write(data['trans_lyrics'])
    
    return True

def main():
    # 确保temp目录存在
    Path("temp").mkdir(exist_ok=True)
    
    try:
        with open("temp.txt", "r+", encoding="utf-8") as f:
            song_ids = [line.strip() for line in f if line.strip()]
            
            # 处理所有ID
            success_count = 0
            for idx, song_id in enumerate(song_ids, 1):
                if process_song(idx, song_id):
                    success_count += 1
                
            # 清空文件内容
            f.seek(0)
            f.truncate()
            
        print(f"处理完成，成功处理 {success_count}/{len(song_ids)} 首歌曲")
    except FileNotFoundError:
        print("错误：temp.txt 文件不存在")

if __name__ == "__main__":
    main()
