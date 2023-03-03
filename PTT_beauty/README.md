# crawl PTT beauty 2022
爬取 2022年度美麗版所有文章
- 想法 : 利用html網址確認需要下載資料的index區間透過爬蟲程式(request + beautifulsoup)完成任務
- 須注意:
    1. 最新資料index無號碼
    2. index會一陣子更新一次(貌似把被刪除文章移除後將文章都往前移動，index會變小)
- 處理:針對第二點有下判斷使其自動往前搜索至正確區間的index

執行方式
1. 爬取2022所有資料，共6000多則訊息
```
python3 main_beauty_2022.py crawl
```
2. 根據給定日期區間(含頭尾)，統計該期間推噓文數，以及排名前10高推文、噓文的作者id
```
python3 main_beauty_2022.py push <start_date> <end_date>
<example> python3 main_beauty_2022.py push 0905 1109
```
 
 

