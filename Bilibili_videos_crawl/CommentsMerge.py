import xml.etree.ElementTree as ET
import pandas as pd
import random
import os

# 参考：https://blog.fachep.com/2020/03/07/Danmaku/#弹幕类型

PATH = 'BV1CY411x7yu_已放弃/《原神》角色演示-「荒泷一斗：哈哈哈哈哈哈哈哈」.cmt.xml' # 视频弹幕信息
cmt_df = pd.read_excel('BV1CY411x7yu_已放弃/Comments.xlsx', index_col=[0]) # 视频评论信息
total_length = 76.00000 # 视频时间信息

"""
用来将评论信息添加到xml文档中去，以便转化为弹幕。
ElementTree 官方参考文档：
https://docs.python.org/zh-cn/3/library/xml.etree.elementtree.html
"""
def merge(xml_path: str, cmt_df: pd.DataFrame, total_length: float, output_path: str):
    tree = ET.parse(xml_path)
    root = tree.getroot()

    # <d p="{time},{type},{size},{color},{timestamp},{pool},{uid_crc32},{row_id}">{Text}</d>
    # p值模板（时间不包括进去），样式为顶部弹幕，颜色为粉色，其它信息不重要，随便填的
    head_p_template = '5,25,16740039,1637157032,0,8aae8059,57706195118796288,10'
    # 正常滚动弹幕
    roll_p_template = '1,25,16740039,1637157032,0,8aae8059,57706195118796288,10'

    time_list = generate_time(max(cmt_df.shape)-1, total_length)
    for i, time in enumerate(time_list):
        temp = cmt_df.iloc[i+1, :]
        is_parent = temp['root'] == 0
        content = temp['content']
        user_name = temp['user']
        # 已放弃顶部弹幕，太过杂乱...
        # str(int(time*100000)/100000) + ',' + head_p_template if is_parent else str(round(time, 5)) + ',' + roll_p_template
        p_content = str(round(time, 5)) + ',' + roll_p_template
        new_ele = ET.Element('d', {'p': p_content})
        new_ele.text = '【' + user_name + '】 ' + content
        root.append(new_ele)
    # 进行覆盖
    if os.path.exists(output_path):
        os.remove(output_path)
    tree.write(output_path, encoding='utf-8')
    print('Successfully merge comments into ' + xml_path + ' ! \n')

"""
返回一系列弹幕出现的时间点。
方法是：将总时间平分成 num 份，然后在每个小区间中点处左右1/3区间长度范围内随机确定弹幕的发送时间。
"""
def generate_time(num: int, total_length: float):
    interval_length = total_length / num
    res = []
    for i in range(num):
        # rand \in [-\frac{1}{3}, \frac{1}{3}]
        rand = random.random()*0.66666-0.3333
        res.append((i+0.5+rand)*interval_length)
    return res

if __name__ == '__main__':
    merge(PATH, cmt_df, total_length, PATH)






