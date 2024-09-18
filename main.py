# 导入所需的库
import argparse
import os
import sys
import ffmpeg
import logging

# 设置日志记录
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def is_video_file(filename):
    """
    检查文件是否为视频文件
    """
    video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv']
    return any(filename.lower().endswith(ext) for ext in video_extensions)

def get_video_duration(input_file):
    """
    获取视频时长
    """
    try:
        probe = ffmpeg.probe(input_file)
        duration = float(probe['streams'][0]['duration'])
        return duration
    except ffmpeg.Error as e:
        logging.error(f"获取视频时长时出错 {input_file}: {e.stderr.decode()}")
        return None

def compress_video(input_file, output_file, target_size_MB=10):
    """
    压缩视频到指定大小
    """
    try:
        # 获取视频时长
        duration = get_video_duration(input_file)
        if duration is None:
            return False

        # 目标大小（以字节为单位）
        target_size_Kb = target_size_MB * 8 * 1024 # 10*8*1024 Kb

        # 音频比特率（Kbps）
        audio_bitrate_Kb = 16

        # 计算视频比特率
        video_bitrate_Kb = (target_size_Kb / duration) - audio_bitrate_Kb
        logging.info(f"时长：{duration} s, 视频码率：{video_bitrate_Kb} Kb, 音频码率：{audio_bitrate_Kb} Kb")
        
        # 确保视频比特率不小于某个最小值（例如 15Kbps）
        min_video_bitrate_Kb = 16
        if video_bitrate_Kb < min_video_bitrate_Kb:
            logging.warning(f"计算的视频比特率过低{video_bitrate_Kb}，使用最小比特率 {min_video_bitrate_Kb} Kbps")
            video_bitrate_Kb = min_video_bitrate_Kb

        # 使用ffmpeg进行视频压缩
        #  -c:v libvpx-vp9 -crf 30 -b:v 100k -maxrate 150k -bufsize 200k -c:a libopus -b:a 16k -application voip -vf 'scale=-2:144'
        process = (
            ffmpeg
            .input(input_file)
            .output(output_file, 
                    vcodec='libvpx-vp9', 
                    crf='30', 
                    video_bitrate=f"{int(video_bitrate_Kb)}k", 
                    maxrate=f"{ 2 * int(video_bitrate_Kb)}k", 
                    bufsize=f"{ 4 * int(video_bitrate_Kb)}k", 
                    acodec='libopus', strict='-2',
                    vbr='on',
                    application='voip',
                    audio_bitrate=f"{audio_bitrate_Kb}k",
                    vf='scale=-2:144')
            .overwrite_output()
            .run_async(pipe_stdout=True, pipe_stderr=True)
        )

        stderr = process.communicate()

        if process.returncode == 0:
            logging.info(f"成功压缩视频: {input_file} -> {output_file}")
            return True
        else:
            logging.error(f"压缩视频时出错 {input_file}: {stderr.decode()}")
            return False
    except ffmpeg.Error as e:
        logging.error(f"压缩视频时出错 {input_file}: {e.stderr.decode()}")
        return False

def process_file(input_file, output_file):
    """
    处理单个文件的函数
    """
    if not is_video_file(os.path.basename(input_file)):
        logging.info(f"跳过非视频文件: {input_file}")
    else:
        compress_video(input_file, output_file)

def main():
    parser = argparse.ArgumentParser(description='Compress video files to under 10MB')
    parser.add_argument('-i', '--input', required=True, help='Input directory')
    parser.add_argument('-o', '--output', required=True, help='Output directory')
    args = parser.parse_args()

    # 检查输入目录是否存在
    if not os.path.exists(args.input):
        logging.error(f"输入目录不存在: {args.input}")
        sys.exit(1)

    # 创建输出目录（如果不存在）
    os.makedirs(args.output, exist_ok=True)

    # 处理文件
    for filename in os.listdir(args.input):
        input_file = os.path.join(args.input, filename)
        # output_filename = f"{os.path.splitext(filename)[0]}_c{os.path.splitext(filename)[1]}"
        output_filename = f"{os.path.splitext(filename)[0]}_c.webm"
        output_file = os.path.join(args.output, output_filename)
        process_file(input_file, output_file)

if __name__ == "__main__":
    main()
