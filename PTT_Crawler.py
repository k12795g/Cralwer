

import requests
import json
import re
from bs4 import BeautifulSoup
import urlextract

# 使用方式：
# 先鎖定要開始爬取的文章，比方說從2022年1月1號開始往2023年爬，那就找出2022年的第一篇文章所在的文章列表的頁面網址，以及該篇文章的標題。
# 1.修改調用Set_Data時的傳入網址
# 2.修改傳入文章標題


# 注意！！！IndexError被我例外化了，由於ptt的文章可以自由編輯，整個文章架構都能被亂刪除，像是推文跟內文直接被砍掉，只剩下殘缺的格式，容易造成index error，所以我將index error的部分直接跳過了。
# 若編寫程式有需要index操作，建議先將Set_Data最後方的except那邊註解掉，方便debug。
# except IndexError as e: 
#     print("error:",e)
#     continue



#去除超連結，實測推文和文章中還經常有：
# https://reurl
# https://imgur.com
# https://i.imgur.com
# https://www.ptt.cc
# 等網址沒消除，有需要的話自己再除錯看看，反正問gpt就是了。
def remove_hyperlinks(text):
    extractor = urlextract.URLExtract()
    urls = extractor.find_urls(text)
    for url in urls:
        text = text.replace(url, '')
    return text


DataList=[]


#tset url:https://www.ptt.cc/bbs/DailyArticle/M.1577930501.A.C92.html
#2020第一篇文章網址
#
# https://www.ptt.cc/bbs/DailyArticle/index594.html
# 該文章所在頁面
#
# [
#     {
#         "Title": "有人吃過嚴萃葉黃素嗎?",
#         "Type": "health",
#         "Author": "Kitty3313 (嗨)",
#         "Date": "Thu Jul 20 13:13:30 2023",
#         "Body": "爬文看了板上分享葉黃素要選游離型分子較小...(以下省略)",
#         "comment": ["太神啦", "原神啟動！"],
#         "Url": "https://www.ptt.cc/bbs/regimen/M.1689830012.A.862.html"
#     }
# ]

def Set_Data(url,first_title):
    Number=int(re.search('index(\d+)\.html',url).group(1)) #用來迭代頁數的變數，抓取輸入網址中的頁數
    
    startup=False
    while (True):
        try:
            print(re.sub('index\d+\.html', f'index{Number}.html', url))
            r=requests.get(re.sub('index\d+\.html', f'index{Number}.html', url)) #用正則表達式處理網址
            Number+=1
            
            if r.status_code == 404: #停止爬蟲條件
                print("404 錯誤：頁面不存在。")
                break
                
            soup=BeautifulSoup(r.text,"html.parser") #載入文章列表網址
            sel=soup.select(".r-ent")
            
            for i in sel:
                Json_Dict={}
                Json_Dict["Type"]="life"
                

                pattern=r"](.*?)\n"
                Json_Dict["Title"]=re.search(pattern,i.select_one("div.title").text, re.DOTALL).group(1).strip()
                
                if(Json_Dict["Title"]!=first_title and not startup): #你要抓的第一篇通常並不在該頁的第一篇，故省略不需要的文章直到第一篇開始。
                    continue
                else: startup=True
                    
                if(not Json_Dict["Title"]):continue #看是否有取到標題，問題通常發生在文章被版主刪除而系統尚未清除時((本文已被刪除) [getniceone])。
                print(Json_Dict["Title"])
                    
                Json_Dict["Url"]="https://www.ptt.cc"+i.select_one("div.title a")['href']
                print(Json_Dict["Url"])
                
                Json_Dict["Author"]=i.select_one("div.meta div.author").text

                article=requests.get(Json_Dict["Url"]) #載入文章網址
                article_soup=BeautifulSoup(article.text,"html.parser")

                Json_Dict["Date"]=article_soup.select("div.article-metaline")[2].text[2:] #這邊用切片切掉了前綴時間兩字

                article_text=article_soup.select("div#main-content")[0].text
                pattern = r"\d{2}:\d{2}:\d{2}\s\d{4}\n(.*?)--\n※ 發信站:" #ptt的內文沒有分隔，只能用正則把他取出來
                Json_Dict["Body"]= re.search(pattern, article_text, re.DOTALL).group(1).strip() #取出後用group(1)匹配第一個()抓到的內容，在用strip()去除頭尾的空白、換行等符號
                Json_Dict["Body"]=remove_hyperlinks(Json_Dict["Body"]) #去除超連結
                Json_Dict["Body"]=re.sub(r'[^\u4e00-\u9fff，。、；：「」『』（）《》？！\s]', '', Json_Dict["Body"]) #去除特殊符號
                Json_Dict["Body"]=re.sub(r'\n+', '\n',Json_Dict["Body"]) #多個換行符號轉成單個
                Json_Dict["Body"]=re.sub('\\s+', ' ',Json_Dict["Body"]) #多個空白符號轉成單個
                
                pattern=":\s(.*?)\s\d{2}/\d{2}"
                if(re.findall(pattern, article_text)): #判斷是否有推文
                    Json_Dict["comment"]=re.findall(pattern, article_text) #抓取推文
                    for i in Json_Dict["comment"]:
                        i=remove_hyperlinks(i) #去除超連結
                        i=re.sub(r'[^\u4e00-\u9fff，。、；：「」『』（）《》？！\s]', '', i) #去除特殊符號
                        i=re.sub(r'\n+', '\n',i) #多個換行符號轉成單個
                        i=re.sub('\\s+', ' ',i) #多個空白符號轉成單個
                else: Json_Dict["comment"]="" #沒推文就給個空字元吧
                    
                print(Json_Dict)
                DataList.append(Json_Dict)
                
            print("已爬取文章數:"+str(len(DataList)))

        except AttributeError as e: 
            print("error:",e)
            continue #由於用到的 group(1)函數，當我們正則沒取到值時會跳出此錯誤，直接捨棄文章不做處理。
            
        except IndexError as e: # 若編寫程式有需要index操作，建議先將Set_Data最後方的except那邊註解掉，方便debug。
            print("error:",e)
            continue

Set_Data("https://www.ptt.cc/bbs/Tainan/index5013.html","水桶") #填入要開始爬取的頁面和起始文章標題。
    


with open("output"+".json","w",encoding='utf-8')as f:
    json.dump(DataList,f,indent=4,ensure_ascii=False) #存檔
print("---結束---")

