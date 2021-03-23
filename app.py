from flask import Flask, render_template, request
from bson.objectid import ObjectId
import tushare as ts
import akshare as ak
import threading
import schedule
import time
import pymongo
import requests
from urllib.parse import quote

mongo_client = pymongo.MongoClient(
    "mongodb://127.0.0.1:27017/?authSource=admin")
db = mongo_client["monitor"]
col = db["sites"]


# 检查基差并发出通知的逻辑
def run_continuously(schedule, interval=1):
    cease_continuous_run = threading.Event()

    class ScheduleThread(threading.Thread):
        @classmethod
        def run(cls):
            while not cease_continuous_run.is_set():
                schedule.run_pending()
                time.sleep(interval)
    continuous_thread = ScheduleThread()
    continuous_thread.start()
    return cease_continuous_run


def check_delta():
    list = col.find()
    for l in list:
      print(l)
      try:
        future = ak.futures_zh_spot(
            subscribe_list="nf_" + l['future'],
            market="FF",
            adjust=False
        ).to_dict()['current_price'][0]
        spot = ts.get_realtime_quotes(l['spot']).to_dict()['price'][0]
        print(float(future) - float(spot))
        if float(future) - float(spot) > float(l['delta']):
          requests.get(
              "https://api.day.app/"+l['key']+"/"+quote('期货'+l['future']+'与现货'+l['spot']+'的基差已到达'+str(float(future) - float(spot)))+"?sound=minuet")
          col.delete_one({"_id": ObjectId(l['_id'])})
      except Exception as e:
        print(e)


schedule.every(10).seconds.do(check_delta)
run_continuously(schedule)



app = Flask(__name__)


@app.route('/')
def index():
    key = request.args.get('key')
    print(key)
    list = col.find(filter={"key": key})
    return render_template('index.html', list=list)


@app.route('/delete_alert', methods=['GET'])
def delete_alert():
  try:
    id = request.args.get('id')
    print(id)
    x = col.delete_one({"_id": ObjectId(id)})
    print(x.deleted_count)
    return render_template('result.html', result='成功')
  except Exception:
    return render_template('result.html', result='失败')

@app.route('/add_alert', methods=['GET', 'POST'])
def add_alert():
    if request.method == 'POST':
      try:
        future = request.form['future']
        spot = request.form['spot']
        delta = request.form['delta']
        key = request.form['key']
        mydict = {"future": future, "spot": spot, "delta": delta, "key": key}
        col.insert_one(mydict)
        return render_template('result.html', result='成功')
      except Exception:
        return render_template('result.html', result='失败')
    else:
        return 

