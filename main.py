import os
import requests
from PIL import Image
from io import BytesIO
from datetime import datetime, timedelta
import json
import logging
import shutil

# 日志配置
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 路径配置
STATIC_FOLDER = "static"
PICTURE_FOLDER = os.path.join(STATIC_FOLDER, "picture")
DAILY_IMAGE_PATH = os.path.join(STATIC_FOLDER, "daily.webp")
INDEX_PATH = os.path.join(PICTURE_FOLDER, "index.json")
MAX_IMAGE_SIZE = (2560, 1600)

# 确保文件夹存在
os.makedirs(PICTURE_FOLDER, exist_ok=True)

def fetch_bing_images(n=8):
    """获取最新的Bing壁纸信息"""
    try:
        url = f"https://www.bing.com/HPImageArchive.aspx?format=js&idx=0&n={n}&uhd=1&mkt=zh-CN"
        resp = requests.get(url)
        resp.raise_for_status()
        data = resp.json()

        images = []
        for image in data["images"]:
            date = datetime.strptime(image["enddate"], "%Y%m%d").strftime("%Y-%m-%d")
            logging.info(f"获取到图片: {date}")
            # 生成高分辨率和备用URL
            urlbase = image["urlbase"]
            high_res_url = f"https://www.bing.com{urlbase}_UHD.jpg"
            fallback_url = f"https://www.bing.com{urlbase}_1920x1080.jpg"

            test_resp = requests.head(high_res_url)
            image_url = high_res_url if test_resp.status_code == 200 else fallback_url

            images.append({
                "date": date,
                "url": image_url,
                "copyright": image.get("copyright", ""),
                "urlbase": urlbase
            })

        return images
    except Exception as e:
        logging.error(f"获取 Bing 图片信息失败: {e}")
        return []

def download_image(url):
    """下载图片并返回PIL Image对象"""
    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        with Image.open(BytesIO(resp.content)) as source:
            image = source.convert("RGB")
        return image, resp.content
    except Exception as e:
        logging.error(f"下载图片失败: {e}")
        return None, None

def load_existing_index():
    """加载现有的index.json文件"""
    if not os.path.exists(INDEX_PATH):
        return []
    
    try:
        with open(INDEX_PATH, "r", encoding="utf-8") as f:
            logging.info("加载现有index.json成功")
            return json.load(f)
    except Exception as e:
        logging.error(f"加载现有index.json失败: {e}")
        return []

def image_paths(date):
    """返回某个日期的三种图片路径"""
    return {
        "filename": f"{date}.webp",
        "path": f"/picture/{date}.webp",
        "jpeg_filename": f"{date}.jpeg",
        "jpeg_path": f"/picture/{date}.jpeg",
        "original_filename": f"{date}-original.jpeg",
        "original_path": f"/picture/{date}-original.jpeg",
    }


def resized_copy(img):
    """生成用于 WebP/JPEG 压缩版本的副本，避免修改原图尺寸"""
    output = img.copy()
    output.thumbnail(MAX_IMAGE_SIZE)
    return output


def save_webp(img, filepath):
    """保存压缩 WebP 图片"""
    try:
        resized_copy(img).save(filepath, "WEBP", quality=80, method=6)
        logging.info(f"保存图片 {filepath}")
        return True
    except Exception as e:
        logging.error(f"保存图片失败 {filepath}: {e}")
        return False


def save_compressed_jpeg(img, filepath):
    """保存压缩 JPEG 图片"""
    try:
        resized_copy(img).save(filepath, "JPEG", quality=95, optimize=True, progressive=True)
        logging.info(f"保存图片 {filepath}")
        return True
    except Exception as e:
        logging.error(f"保存图片失败 {filepath}: {e}")
        return False


def save_original_jpeg(img, original_bytes, filepath):
    """保存原始 JPEG 字节，无法使用原始字节时再回退为无损质量导出"""
    try:
        if original_bytes:
            with open(filepath, "wb") as output:
                output.write(original_bytes)
        else:
            img.save(filepath, "JPEG", quality=100)
        logging.info(f"保存图片 {filepath}")
        return True
    except Exception as e:
        logging.error(f"保存图片失败 {filepath}: {e}")
        return False


def normalize_item(item):
    """为旧索引补齐三种格式的标准文件字段"""
    normalized = dict(item)
    normalized.update(image_paths(item["date"]))
    return normalized


def ensure_image_files(item, download_cache):
    """补齐某个历史日期缺失的图片格式"""
    date = item["date"]
    paths = image_paths(date)
    targets = {
        "webp": os.path.join(PICTURE_FOLDER, paths["filename"]),
        "jpeg": os.path.join(PICTURE_FOLDER, paths["jpeg_filename"]),
        "original": os.path.join(PICTURE_FOLDER, paths["original_filename"]),
    }
    missing = [kind for kind, filepath in targets.items() if not os.path.exists(filepath)]
    if not missing:
        return

    url = item.get("url")
    if not url:
        logging.warning(f"图片 {date} 缺少源地址，无法补齐格式")
        return

    if date not in download_cache:
        download_cache[date] = download_image(url)
    img, original_bytes = download_cache[date]
    if img is None:
        return

    if "webp" in missing:
        save_webp(img, targets["webp"])
    if "jpeg" in missing:
        save_compressed_jpeg(img, targets["jpeg"])
    if "original" in missing:
        save_original_jpeg(img, original_bytes, targets["original"])


def sync_daily_files(item):
    """将最新日期的三种历史格式同步为根目录下的兼容文件"""
    paths = image_paths(item["date"])
    file_pairs = (
        (os.path.join(PICTURE_FOLDER, paths["filename"]), DAILY_IMAGE_PATH),
        (os.path.join(PICTURE_FOLDER, paths["jpeg_filename"]), os.path.join(STATIC_FOLDER, "daily.jpeg")),
        (os.path.join(PICTURE_FOLDER, paths["original_filename"]), os.path.join(STATIC_FOLDER, "original.jpeg")),
    )

    for source, target in file_pairs:
        if not os.path.exists(source):
            logging.warning(f"最新图片文件不存在，无法同步: {source}")
            continue
        shutil.copyfile(source, target)
        logging.info(f"同步最新图片: {source} -> {target}")

def merge_and_update_images(new_images, existing_index):
    """合并新图片和现有索引，并更新文件"""
    logging.info(f"今天的日期: {datetime.now().strftime('%Y-%m-%d')}")
    images_by_date = {}

    # 先保留已有索引，再用最新接口数据更新元信息
    for item in existing_index:
        if item.get("date"):
            images_by_date[item["date"]] = dict(item)

    for img_info in new_images:
        date = img_info["date"]
        logging.info(f"处理图片: {date}")
        existing = images_by_date.get(date, {})
        existing.update({
            "date": date,
            "copyright": img_info.get("copyright", existing.get("copyright", "")),
            "url": img_info.get("url", existing.get("url", "")),
        })
        images_by_date[date] = existing

    # 按日期排序（最新的在前面）
    combined_index = [normalize_item(item) for item in images_by_date.values()]
    combined_index.sort(key=lambda x: x["date"], reverse=True)

    # 保留最近30天的数据
    thirty_days_ago = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    filtered_index = []
    removed_files = set()

    for item in combined_index:
        if item["date"] > thirty_days_ago:
            filtered_index.append(item)
        else:
            paths = image_paths(item["date"])
            for key in ("filename", "jpeg_filename", "original_filename"):
                removed_files.add(os.path.join(PICTURE_FOLDER, paths[key]))
            legacy_filename = item.get("filename")
            if legacy_filename:
                removed_files.add(os.path.join(PICTURE_FOLDER, os.path.basename(legacy_filename)))
            logging.info(f"图片 {item['date']} 超过30天，标记为删除")

    # 为所有保留日期补齐 WebP、压缩 JPEG 和原始 JPEG
    download_cache = {}
    for item in filtered_index:
        ensure_image_files(item, download_cache)

    # 最新一张继续输出根目录下的兼容文件，供 /api/daily 使用
    if filtered_index:
        sync_daily_files(filtered_index[0])

    # 删除超过30天的旧图片
    for filepath in removed_files:
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
                logging.info(f"删除旧图片: {filepath}")
        except Exception as e:
            logging.error(f"删除旧图片失败 {filepath}: {e}")
    
    return filtered_index

def update_index(index_list):
    """更新index.json文件"""
    try:
        with open(INDEX_PATH, "w", encoding="utf-8") as f:
            json.dump(index_list, f, ensure_ascii=False, indent=2)
        logging.info(f"已更新 index.json，共 {len(index_list)} 项")
    except Exception as e:
        logging.error(f"更新index.json失败: {e}")

def main():
    logging.info("开始获取 Bing 图片...")
    existing_index = load_existing_index()
    new_images = fetch_bing_images(8)

    if not new_images:
        logging.error("未获取到任何新图像信息")
        return

    updated_index = merge_and_update_images(new_images, existing_index)
    update_index(updated_index)

if __name__ == "__main__":
    main()
