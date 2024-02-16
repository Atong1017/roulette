import requests, time, os, threading, subprocess, pandas as pd, cv2
import tkinter as tk, tkinter.ttk as ttk
from datetime import datetime
from dateutil.parser import parse
from tkintertable.Tables import TableCanvas
from adbutils import adb
from sqlalchemy import create_engine
import pyodbc
import numpy as np
from PIL import Image as im
import ddddocr
from Tool.sqlcmd import MSSQL
import asyncio


class Stake_Simulate:

    """ ------------------------------------------ 表格 -------------------------------------------------------------"""
    # 新增任務
    def add_task(self, *args):
        input_data = args

        data_list = [self.data]

        if self.count_data == 0:
            del self.data[0]

        # dict的key值
        self.count_data += 1
        # 下單列表
        bs = None
        # 上升策略選項
        up_check = ''
        if self.up_var.get() == 1:
            up_check = '(上升)'
        # 判斷是否需加倍下單
        x2 = "X1"
        if self.x2_var.get() == 1:
            x2 = "X2"

        up_profit = int(self.up_profit.get())
        up_front = int(self.up_front.get())
        up_later = int(self.up_later.get())

        # 無帶入值時，下單資訊從tk下載
        if len(input_data) == 0:
            bettype = self.bet_type.get()                                       # 下單策略
            hs = self.bet_history.get()                                         # 歷史記錄
            bt = self.bet_time.get()                                            # 最多連錯次數
            amount = float(self.start_amount.get())                             # 模擬器當前金額
            chips = float(self.chips.get())                                     # 每單籌碼
            emulator = self.bet_emulator.get()                                  # 要執行的模擬器
            if '自訂組數' in bettype:
                bc = self.bet_self.get()                                        # 下單數
                bs = [int(a.strip()) for a in self.bet_self.get().split(',')]   # 下單列表
            else:
                bc = self.bet_count.get()

        else:
            bet_info = input_data[0]['Bet_Type'].split('--')
            bettype = bet_info[0]

            if '歷史筆數' in bettype:
                hs = bet_info[1]
                bc = bet_info[2]
                bt = bet_info[3]

            else:
                hs = ''
                bc = bet_info[1]
                bt = bet_info[2]
            if '自訂組數' in bettype:
                bs = input_data[0]['Bet']

            amount = input_data[0]['Amount']
            chips = input_data[0]['Chips']
            emulator = input_data[0]['Emulator']

        start_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 新增一筆交易，key=self.count_data，Bet_Type': None, '號碼': None, 'Bet': None, 'Next_bet
        for di, da in enumerate(data_list):
            if '歷史筆數' in bettype:
                da[self.count_data] = {'Bet_Type': f"{bettype + up_check}--{hs}--{bc}--{bt}--{x2}"}
            else:
                da[self.count_data] = {'Bet_Type': f"{bettype + up_check}--{bc}--{bt}--{x2}"}

            da[self.count_data]['Amount'] = amount
            da[self.count_data]['Chips'] = chips
            da[self.count_data]['Start_Amount'] = amount
            da[self.count_data]['Emulator'] = emulator

            da[self.count_data]['Bet_Mode'] = emulator

            da[self.count_data]['Number'] = None
            da[self.count_data]['Bet'] = bs
            da[self.count_data]['Next_bet'] = bs

            da[self.count_data]['Start_Date'] = start_datetime
            da[self.count_data]['no_award'] = 1000
            da[self.count_data]['Stop_time'] = 0
            da[self.count_data]['Uninterrupted'] = 0
            da[self.count_data]['Consecutive_Win'] = 0

            da[self.count_data]['High'] = -1
            da[self.count_data]['Low'] = 100000000
            da[self.count_data]['Profit'] = float(self.profit.get())
            da[self.count_data]['StopLoss'] = float(self.loss.get())

            da[self.count_data]['Reduce'] = int(self.hs_deduct.get())
            da[self.count_data]['First_Reduce'] = int(self.first_reduce.get())
            da[self.count_data]['Second_Reduce'] = int(self.second_reduce.get())

            da[self.count_data]['Up_Profit'] = up_profit
            da[self.count_data]['Up_Front'] = up_front
            da[self.count_data]['Up_Later'] = up_later
            da[self.count_data]['Order_Quantity'] = 0

            # 新增一筆交易時間，key=self.count_data
            self.pre_time_dict[self.count_data] = datetime.now()

        # 存入db之欄位
        column_name = "Amount, Strategy, Up_Profit, Up_Front, Up_Later, Emulator, CreateTime, Status"
        cursor, conn = self.sql_server.connect_mssql()

        # 抓模擬器金額
        try:
            # 所有模擬器列表
            e_list = adb.device_list()
            # 要抓取的模擬器編號
            em = int(emulator) - 1

            amount = self.balance(emulator_port=e_list[em].serial)

            da[self.count_data]['Amount'] = float(amount)
            da[self.count_data]['Start_Amount'] = float(amount)
            self.start_amount.delete(0, 'end')
            self.start_amount.insert(0, str(amount))

            # 更新表格
            self.update_table(self.table, self.data, self.data1)
        except:
            # 金額有誤時，改使用tk上之金額
            amount = float(self.start_amount.get())
            print("****************************************** 存入金額有誤 ******************************************")

        if '歷史筆數' in bettype:
            bet_type = f"{bettype + up_check}--{hs}--{bc}--{bt}--{x2}"
        else:
            bet_type = f"{bettype + up_check}--{bc}--{bt}--{x2}"
        data = [(
            amount,
            bet_type,
            up_profit,
            up_front,
            up_later,
            emulator,
            start_datetime,
            0
        )]

        # 存入db
        self.sql_server.insert_data_to_sql(data, 'Start_Amount', column_name, cursor, conn)

        # 關閉連接
        cursor.close()
        conn.close()

    # 刪除任務
    def delete_task(self):
        if len(self.data) > 0 or len(self.data) < self.table.getSelectedRow():
            keylist = list(self.data.keys())
            keyname = keylist[self.table.getSelectedRow()]
            del self.data[keyname]
            del self.pre_time_dict[keyname]

            # 更新表格
            self.update_table(self.table, self.data, self.data1)

    # 更新任務
    def update_task(self):
        # 選中的self.data值
        keylist = list(self.data.items())[self.table.getSelectedRow()]
        bettype = self.bet_type.get()                                   # 策略類型
        hs = self.bet_history.get()                                     # 歷史記錄
        bt = self.bet_time.get()                                        # 未中次數

        # 上升策略選項
        up_check = ''
        if self.up_var.get() == 1:
            up_check = '(上升)'

        # 加倍
        x2 = "X1"
        if self.x2_var.get() == 1:
            x2 = "X2"

        up_profit = int(self.up_profit.get())
        up_front = int(self.up_front.get())
        up_later = int(self.up_later.get())

        # 下單數
        if '自訂組數' in bettype:
            bc = self.bet_self.get()
        else:
            bc = int(self.bet_count.get())

        # 新的策略名稱
        if '歷史筆數' in bettype:
            btt = {'Bet_Type': f"{bettype + up_check}--{hs}--{bc}--{bt}--{x2}"}
        else:
            btt = {'Bet_Type': f"{bettype + up_check}--{bc}--{bt}--{x2}"}

        self.data[keylist[0]]['Bet_Type'] = btt['Bet_Type']

        emulator = self.bet_emulator.get()  # 模擬器編號

        self.data[keylist[0]]['Emulator'] = emulator
        self.data[keylist[0]]['Bet_Mode'] = emulator
        self.data[keylist[0]]['Number'] = []
        self.data[keylist[0]]['Bet'] = []
        self.data[keylist[0]]['Next_Bet'] = []

        # ===== 停止下單參數 =====
        self.data[keylist[0]]['no_award'] = 1000
        self.data[keylist[0]]['Stop_time'] = 0
        self.data[keylist[0]]['Uninterrupted'] = 0
        self.data[keylist[0]]['Consecutive_Win'] = 0

        # ===== 停利/損參數 =====
        self.data[keylist[0]]['Profit'] = float(self.profit.get())
        self.data[keylist[0]]['StopLoss'] = float(self.loss.get())

        # ===== 交集參數 =====
        self.data[keylist[0]]['Reduce'] = int(self.hs_deduct.get())
        self.data[keylist[0]]['First_Reduce'] = int(self.first_reduce.get())
        self.data[keylist[0]]['Second_Reduce'] = int(self.second_reduce.get())

        # ===== 上升參數 =====
        self.data[keylist[0]]['Up_Profit'] = up_profit
        self.data[keylist[0]]['Up_Front'] = up_front
        self.data[keylist[0]]['Up_Later'] = up_later
        self.data[keylist[0]]['Order_Quantity'] = 0

        # 更新表格
        self.update_table(self.table, self.data, self.data1)

        # 存入db
        column_name = "Amount, Strategy, Up_Profit, Up_Front, Up_Later, Emulator, CreateTime, Status"
        cursor, conn = self.sql_server.connect_mssql()
        try:
            # 所有模擬器列表
            e_list = adb.device_list()
            # 要抓取的模擬器編號
            em = int(emulator) - 1

            amount = self.balance(emulator_port=e_list[em].serial)

            self.data[keylist[0]]['Amount'] = float(amount)
            self.data[keylist[0]]['Start_Amount'] = float(amount)
            self.start_amount.delete(0, 'end')
            self.start_amount.insert(0, str(amount))
        except:
            amount = float(self.start_amount.get())
            print("****************************************** 存入金額有誤 ******************************************")

        if '歷史筆數' in bettype:
            bet_type = f"{bettype + up_check}--{hs}--{bc}--{bt}--{x2}"
        else:
            bet_type = f"{bettype + up_check}--{bc}--{bt}--{x2}"
        data = [(
            amount,
            bet_type,
            up_profit,
            up_front,
            up_later,
            emulator,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            1
        )]
        self.sql_server.insert_data_to_sql(data, 'Start_Amount', column_name, cursor, conn)

        # 關閉連接
        cursor.close()
        conn.close()

    # 表格更新
    def update_table(self, table, data, data1):
        # 獲取表格的model對象
        model = table.model
        new_data = {k: {k1: v1 for k1, v1 in v.items() if
                        k1 not in ['Chips', 'Start_Date', 'no_award', 'Stop_time', 'Uninterrupted']} for k, v in
                    data.items()}

        # 在数据字典中新增一行
        model.deleteRows()
        model.importDict(new_data)

        # 使用字典推導式提取所有'Bet_Type'鍵對應的值
        keyslist = list(data1.keys())
        cellw = []
        for j, k in enumerate(keyslist):
            a = [v[k] for v in new_data.values() if k in v]
            b = 0
            for aa in a:
                if len(str(aa)) > b:
                    b = len(str(aa))

            # 欄位寬度
            if j == 0:
                cellw.append(160 + (b - 18) * 10)
            elif j == 1:
                if b > 4 and 100 + (b - 20) * 3.5 > 80:
                    cellw.append(100 + (b - 20) * 3.5)
                else:
                    cellw.append(80)
            elif j == 2:
                cellw.append(60)
            elif j == 3:
                cellw.append(40)
            elif j > 3:
                if b > 4 and 110 + (b - 20) * 3.5 > 100:
                    cellw.append(110 + (b - 20) * 3.5)
                else:
                    cellw.append(100)

        i = 0
        while i < len(cellw):
            table.resizeColumn(i, cellw[i])
            i += 1
        table.redrawTable()

    """ ------------------------------------------ 資料庫相關 ------------------------------------------------------ """

    # 所有已開的號碼資訊
    def history_number(self, top_count=''):
        if top_count != '':
            top_count = f'Top({top_count})'
        sql = f"""
                ;WITH CET AS (
                    SELECT ROW_NUMBER() OVER (ORDER BY ID, CreateTime) AS [Row],
                       *
                    FROM Roulette
                    WHERE Status = 0 AND Result BETWEEN 0 AND 36 )
                SELECT {top_count} *
                    FROM CET                    
                    ORDER BY CreateTime DESC, [Row] DESC  
            """

        cursor, conn = self.sql_server.connect_mssql()

        cursor.execute(sql)
        history_list = cursor.fetchall()

        # 關閉連接
        cursor.close()
        conn.close()

        return history_list

    # 每個數字出現次數，history_list=Row, ID, Result, CreateTime、hs=歷史數
    def calculate_history_rank(self, history_list, hs):

        number_counts = {}
        for i in range(37):
            number_counts[i] = [0, 0]

        # 記錄每個數字的出現次數
        for si, sublist in enumerate(history_list[:hs][::-1]):
            try:
                s = sublist[2]
                sii = sublist[0]
            except:
                s = sublist
                sii = si
            number_counts[s][0] += 1
            number_counts[s][1] = sii

        # 使用sorted函數進行排序
        number_counts = sorted(number_counts.items(), key=lambda x: (-x[1][0], -x[1][1]))

        return number_counts

    # 每個數字後面數字出現之次數
    def calculate_top_rank(self, data):
        # 篩選出只剩號碼之列表
        numbers = [a[2] for a in data[::-1]]

        # 計算起始值
        top_dict = {}
        for j in range(37):
            top_dict[j] = {}
            for i in range(37):
                top_dict[j][i] = 0

        # 後面數字每出現一次+1
        i = 0
        while i < len(numbers) - 1:
            first_num = numbers[i]
            # 後面數字
            second_num = numbers[i + 1]

            # 相對應號碼次數+1
            top_dict[first_num][second_num] += 1

            i += 1

        # 每個value重新排序
        top_dict = sorted(top_dict[numbers[-1]].items(), key=lambda x: -x[1])

        return top_dict

    """ ------------------------------------------ 程式執行 -------------------------------------------------------- """

    # 開始
    def start_bet(self):
        # 開始判斷模擬器網頁是否正常
        self.threadbutton('device_screenshot')

        while 1:

            # 所有data key值
            keys = list(self.data.keys())

            # ===  抓最新單筆開單資訊(Row, ID, Result, CreateTime, Status
            data = self.history_number('1')[0]
            # 最新號碼
            open_number = data[2]
            # 最新開單時間
            input_date = data[3]

            # 判斷是否開出新號碼，沒有則等1秒再偵測
            if input_date > self.pre_time_dict[keys[0]]:
                self.pre_time_dict[keys[0]] = input_date

            else:
                time.sleep(1)
                continue

            # ======================================= 找出最大歷史筆數及是否有top值
            all_history = self.history_number()  # 找出所有已開號碼資訊(Row, ID, Result, CreateTime, Status

            """ ======================================= 執行所有策略 ======================================= """
            #
            asyncio.run(self.bet_main(open_number, all_history))

            # 所有要下單的key值
            bet_key = list(self.all_bets.keys())

            # 按模擬器下單
            for b in bet_key:
                self.threadbutton('bet_chips', (self.all_bets[b], b,))

            print("停止下單!!!!!!!!")
            time.sleep(5)

            # 所有下單資訊歸零
            self.all_bets = {}

            e_list = adb.device_list()
            keys = list(self.notify_info.keys())
            values = list(self.notify_info.values())

            k = 0
            while k < len(keys):
                if values[k] == 1:
                    em = keys[k]
                    amount = self.balance(emulator_port=e_list[em].serial)
                    try:

                        oldamount = self.data[keys[k] + 1]['Start_Amount']

                        if amount / float(oldamount) >= 1.1:
                            self.data[keys[k] + 1]['Emulator'] = ''

                        self.data[keys[k] + 1]['Amount'] = amount

                    except:
                        amount = '出錯!!!!'

                    self.LineNotify(f'\n'                                                                     
                                    f'模擬器:{em + 1}\n'
                                    f'金額：{amount}')

                    k += 1

            # 更新表格
            self.update_table(self.table, self.data, self.data1)
            # 通知資訊歸零
            self.notify_info = {}

    #
    async def bet_main(self, open_number, all_history):
        keys = list(self.data.keys())
        tasks = []
        i = 0
        while i < len(keys):
            self.data[keys[i]]['Number'] = open_number
            task = asyncio.create_task(self.bet_calculate(all_history, keys[i], 20))
            if task:
                tasks.append(task)

            i += 1

        # 執行收集到的所有線程tasks，因tasks為list，需用*打開
        results = await asyncio.gather(*tasks)

        return results, time.time()

    #
    async def bet_calculate(self, data, key, show):
        if self.data[key]['Emulator'] != '':
            a = await asyncio.to_thread(lambda: self.strategy_analyze(data, key, show))

            return show, key, a

    #
    def strategy_analyze(self, data, key, show, chips=1):
        lnt = 0
        bettype = self.data[key]['Bet_Type']
        bet_info = bettype.split('--')

        up_r = 0  # 用來分辨bet_list狀態
        up_text = ''
        startdate = self.data[key]['Start_Date']

        open_number = self.data[key]['Number']
        if '歷史筆數' in bettype:
            hs = int(bet_info[1])
            bc = int(bet_info[2])
            bt = int(bet_info[3])
            bet_x2 = bet_info[4]
        elif '自訂' in bettype:
            bc = len(bet_info[1].split(','))
            bt = int(bet_info[2])
            bet_x2 = bet_info[3]
        else:
            bc = int(bet_info[1])
            bt = int(bet_info[2])
            bet_x2 = bet_info[3]

        bet_list = []
        # --------------------------------------------------------------------------------------------------------------------------------------------------------------------------
        if '歷史筆數' in bettype:

            # 要下單的號碼:號碼, 次數
            data_info = self.calculate_history_rank(data, hs)
            bet_list = [a[0] for a in data_info][:bc]

        elif '自訂組數' in bettype:
            # bet_list = self.data[key]['Next_bet']
            bet_list = [int(a) for a in bet_info[1].split(',')]

        elif 'Top' in bettype:
            data_info = self.calculate_top_rank(data)

            bet_list = [a[0] for a in data_info[:bc]]

        elif '號碼-+' in bettype:
            d = int(bc)
            a = list(range(37))
            if open_number - d < 0:
                bet_list = a[open_number - d:] + a[:open_number + d + 1]
            elif open_number + d > 36:
                bet_list = a[open_number - d:] + a[:open_number + d - 36]
            else:
                bet_list = a[open_number - d:open_number + d + 1]

        elif '交集' in bettype:

            reduce = self.data[key]['Reduce']

            bet_list = asyncio.run(self.strategy_main(data, reduce, bc, bt, i + 1))
            self.mixed = bet_list[1]
            bet_list = bet_list[0]

        self.data[key]['Bet'] = self.data[key]['Next_bet']
        # print(9999999999999999, bettype, bet_list)
        self.data[key]['Next_bet'] = bet_list

        amount = self.data[key]['Amount']
        no_award = self.data[key]['no_award']
        pre_bet_list = [] if self.data[key]['Bet'] is None else self.data[key]['Bet']
        chips = self.data[key]['Chips']
        nr = self.result_info(open_number, pre_bet_list, bt, no_award, amount, chips)

        if '上升' in bettype:
            up_profit = float(self.data[key]['Up_Profit'])      # 獲利值
            up_front = float(self.data[key]['Up_Front'])        # 往前計算筆數
            interval = up_front + 1
            up_later = float(self.data[key]['Up_Later'])        # 往後下單次數
            # 尚未執行上升
            if self.data[key]['Order_Quantity'] == 0:
                rr = self.strategy_result(data, bettype, 20)
                a = self.cumulative_front(rr[1], i=1, cs=up_profit, interval=interval)
                if a:
                    print('rr:', rr[2], 'nr:', nr)
                    self.data[key]['Order_Quantity'] = 1
                    self.data[key]['no_award'] = rr[2][-1]
                    if rr[2][-1] <= bt:
                        up_r = 1
                    else:
                        up_r = 3
                else:
                    up_r = 0

                up_text = f" -- Order_Times:{self.data[key]['Order_Quantity']}"

            # 已執行
            else:
                self.data[key]['no_award'] = nr[1]
                self.data[key]['Order_Quantity'] += 1
                up_text = f" -- Order_Times:{self.data[key]['Order_Quantity']}"
                # 勝場通知
                if nr[2] == 1:
                    lnt = 1
                if nr[1] <= bt:
                    up_r = 2
                else:
                    up_r = 3

            if self.data[key]['Order_Quantity'] >= up_later:
                self.data[key]['Order_Quantity'] = 0
                lnt = 2

        # 非上升之策略
        else:
            if nr[1] > bt:
                if nr[1] == bt + 1:
                    lnt = 2
                up_r = 0

            else:
                if nr[2] == 2:
                    up_r = 1
                else:
                    up_r = 2
                    if nr[2] == 1:
                        lnt = 1
            self.data[key]['no_award'] = nr[1]

        if lnt == 1:
            print(f"******* Win!!! *** ({open_number}) *** Bet:{bet_list} -- {bettype}")
        if up_r == 0:
            print(f"Stop Bet  *** ({open_number}) *** Bet:{bet_list} -- {bettype} -- no_award:{nr[1]} --Win/Lose:{nr[2]}")
            bet_list = []
        elif up_r == 1:
            print(f"Start Bet *** ({open_number}) *** Bet:{bet_list}{up_text} -- {bettype} -- no_award:{nr[1]} --Win/Lose:{nr[2]}")
        elif up_r == 2:
            print(f"---- no_award({self.data[key]['no_award']}) *** ({open_number}) *** Bet:{bet_list}{up_text} -- {bettype} -- no_award:{nr[1]} --Win/Lose:{nr[2]}")
        elif up_r == 3:
            print(f"Wait Bet  *** ({open_number}) *** Bet:{bet_list}{up_text} -- {bettype} -- no_award:{nr[1]} --Win/Lose:{nr[2]}")
            bet_list = []

        # print(777777788888888888888888, bet_list)
        notify_number = f"S{100 + key}"
        eps = int(self.data[key]['Emulator']) - 1

        # 勝場通知
        if lnt == 1:
            self.notify_info[eps] = 1
            try:
                self.LineNotify(f'\n'
                                f'Winning！ -- {open_number}\n'
                                f"{bettype[:-4]}\n"
                                f'{notify_number} -- Chips:{chips}\n'
                                f'Order：{pre_bet_list}\n'
                                f'Start:{startdate}')
            except:
                pass
        # 停止下單通知
        if lnt == 2:
            print(f"1111111111111111{bettype}11111111111111111111")
            try:
                self.notify_info[eps] = 1
                self.LineNotify(f'Stop！{bettype[:-4]}\n'
                                f'{notify_number} -- Chips:{chips}\n'                          
                                f'Start:{startdate}')
            except:
                pass

        try:

            self.all_bets[eps] += bet_list

        except:
            self.all_bets[eps] = bet_list

        # self.bet_chips(bet_list, eps)

        return bettype, bet_list

    #
    def result_info(self, open_numer, bet_list, continuous_error, no_award, amount, chips):
        # 0:下單中，輸、1:下單中，贏、2:開始下單、3:停止下單
        if open_numer in bet_list:
            count_nums = bet_list.count(open_numer)
            # 表示此筆之前已有下單，所以有中
            if no_award <= continuous_error:
                # 贏的獎項
                amount += chips * 36 * count_nums
                wl = 1
            else:
                # 此筆前無下單，所以只是開始下單
                wl = 2

            # 無論此筆前有無下單，皆重新迴圈下單
            no_award = 0
            amount -= chips * len(bet_list)

        else:
            # 表示此筆之前已有下單，輸
            if no_award < continuous_error:
                amount -= chips * len(bet_list)
                wl = 0
            else:
                # 此筆前無下單，所以無任何動作
                wl = 3

        no_award += 1

        return amount, no_award, wl

    # 策略結果計算，用以列出往前的open number, amount, win/lose
    def strategy_result(self, data, bettype, show, chips=1):
        no_award = 1000
        amount = 0
        high_amount = -1
        low_amount = 100000000

        open_numer_list = []
        no_award_list = []
        amount_list = []
        high_amount_list = []
        low_amount_list = []
        wl_list = []
        open_time_list = []

        if '歷史筆數' in bettype:
            history = int(bettype.split('--')[1])
            bet_set = int(bettype.split('--')[2])
            continuous_error = int(bettype.split('--')[3])

            # 歷史紀錄+顯示筆數, 並使其從舊到新排序
            history_list = data[:history + show][::-1]

            i = 0
            while i < show:
                number_counts = {}
                for j in range(37):
                    number_counts[j] = [0, 0]

                # 最新號碼之前的歷史筆數
                hs = history_list[i:history + i]

                # 記錄歷史筆數每個數字的出現次數
                for sublist in hs:
                    number_counts[sublist[2]][0] += 1
                    number_counts[sublist[2]][1] = sublist[0]

                # 使用sorted函數進行排序
                number_counts = sorted(number_counts.items(), key=lambda x: (-x[1][0], -x[1][1]))

                number_counts = [a[0] for a in number_counts][:bet_set]

                open_numer = history_list[history + i][2]

                open_time = history_list[history + i][3].strftime('%Y-%m-%d %H:%M')

                amount, no_award, wl = self.result_info(open_numer, number_counts, continuous_error, no_award,
                                                        amount, chips)

                if amount > high_amount:
                    high_amount = amount
                elif amount <= low_amount:
                    low_amount = amount

                open_time_list.append(open_time)
                open_numer_list.append(open_numer)
                no_award_list.append(no_award)
                amount_list.append(amount)
                high_amount_list.append(high_amount)
                low_amount_list.append(low_amount)
                wl_list.append(wl)

                i += 1

        elif '號碼-+' in bettype:
            # 僅顯示筆數, 並使其從舊到新排序
            history_list = data[:show + 1][::-1]
            bet_set = int(bettype.split('--')[1])
            continuous_error = int(bettype.split('--')[2])

            on = history_list[0][2]
            d = int(bet_set)
            a = list(range(37))
            if on - d < 0:
                next_bet = a[on - d:] + a[:on + d + 1]
            elif on + d > 36:
                next_bet = a[on - d:] + a[:on + d - 36]
            else:
                next_bet = a[on - d:on + d + 1]

            i = 1
            while i < len(history_list):
                h = history_list[i]
                pre_bet = next_bet
                open_numer = h[2]
                open_time = h[3].strftime('%Y-%m-%d %H:%M')

                on = history_list[i][2]
                d = int(bet_set)
                a = list(range(37))
                if on - d < 0:
                    next_bet = a[on - d:] + a[:on + d + 1]
                elif on + d > 36:
                    next_bet = a[on - d:] + a[:on + d - 36]
                else:
                    next_bet = a[on - d:on + d + 1]

                amount, no_award, wl = self.result_info(open_numer, pre_bet, continuous_error, no_award, amount,
                                                        chips)

                # print(open_numer, pre_bet, next_bet, amount, no_award, wl)

                if amount > high_amount:
                    high_amount = amount
                elif amount <= low_amount:
                    low_amount = amount

                open_time_list.append(open_time)
                open_numer_list.append(open_numer)
                no_award_list.append(no_award)
                amount_list.append(amount)
                high_amount_list.append(high_amount)
                low_amount_list.append(low_amount)
                wl_list.append(wl)

                i += 1

        elif 'Top' in bettype:
            # 所有號碼
            # print(11111111111, data[0])
            results = [a[2] for a in data][::-1]
            open_time_list = [a[3] for a in data][::-1]
            bts = bettype.split('--')
            bet_set = int(bts[1])
            continuous_error = int(bts[2])

            # 用以計算次數之資料
            results_len = len(results)

            shows = 0
            # 所有需要用到的計算+顯示號碼
            top_list = results[shows:-show]

            # 顯示筆數
            showlist = results[-show:]

            # 計算起始值
            top_dict = {}
            for j in range(37):
                top_dict[j] = {}
                for i in range(37):
                    top_dict[j][i] = 0

            # 後面數字每出現一次+1
            i = 0
            num = 37
            while i < len(top_list):
                # 最後一組號碼
                if i == len(top_list) - 1:
                    num = showlist[0]
                else:
                    num = top_list[i + 1]
                # 相對應號碼次數+1
                top_dict[top_list[i]][num] += 1

                i += 1

            # 顯示筆數每新增一組號碼時，號碼次數+1
            for si, open_numer in enumerate(showlist):
                if si == 0:
                    pre_bet = sorted(top_dict[top_list[-1]].items(), key=lambda x: (-x[1]))
                else:
                    pre_bet = sorted(top_dict[showlist[si - 1]].items(), key=lambda x: (-x[1]))
                pre_bet = [a[0] for a in pre_bet][:bet_set]

                amount, no_award, wl = self.result_info(open_numer, pre_bet, continuous_error, no_award, amount,
                                                        chips)

                if amount > high_amount:
                    high_amount = amount
                elif amount <= low_amount:
                    low_amount = amount

                open_numer_list.append(open_numer)
                no_award_list.append(no_award)
                amount_list.append(amount)
                high_amount_list.append(high_amount)
                low_amount_list.append(low_amount)
                wl_list.append(wl)

                # 新增號碼新增進入top值
                top_dict[num][open_numer] += 1

        return open_numer_list, amount_list, no_award_list

    # 每筆往前計算總合
    def cumulative_front(self, data_list, i=1, cs=80, interval=20):
        # 計算金額總合
        # print(7777777777, data_list)
        cumulative_sum = 0
        data_list = data_list[::-1]

        while i < len(data_list):

            cumulative_sum = data_list[0] - data_list[i]
            if cumulative_sum >= cs:
                return i, cumulative_sum

            i += 1

    """ ------------------------------------------ 模擬器相關 ------------------------------------------------------ """

    # 螢幕截圖(0:只截圖、1:將截圖存檔)
    def screenshot(self, save=0, pngname='screencap', emulator_port=''):
        if save == 1:
            subprocess.check_output(
                f'adb -s {emulator_port} shell /system/bin/screencap -p /sdcard/{pngname}.png', shell=True)
            subprocess.check_output(
                f'adb -s {emulator_port} pull /sdcard/{pngname}.png ./../png/{pngname}.png', shell=True)
        else:
            pipe = subprocess.Popen(f"adb -s {emulator_port} shell screencap -p", stdin=subprocess.PIPE,
                                    stdout=subprocess.PIPE, shell=True)
            image_bytes = pipe.stdout.read().replace(b'\r\n', b'\n')
            try:
                image = cv2.imdecode(np.frombuffer(image_bytes, dtype=np.uint8), cv2.IMREAD_COLOR)
            except:
                image = None

            return image

    # 配對圖片=>0:直接點擊符合的中心點，1:回傳是否找到，2:使用記憶體之預存圖，並回傳是否找到
    def matchpng(self, png_name, screenshot, click=0, resolution=0.99, emulator_port=''):

        prepared = cv2.imread(f'./../png/{png_name}.png')

        result = cv2.matchTemplate(screenshot, prepared, cv2.TM_CCORR_NORMED)

        # 取得搜尋結果最大值、最小值
        # 計算矩陣 Mat 中最大值、最小值、返回最大最小的索引
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

        if max_val >= resolution:
            # TM_CCORR_NORMED 最大值
            mat_top, mat_left = max_loc

            # 取得目標取樣的高度及寬度
            # image.shape = (height, width, channels)
            prepared_height, prepared_width, prepared_channels = prepared.shape

            # 取得需要繪製終點的右下位置(左上 + 高, 左上 + 寬)
            bottom_right = (mat_top + prepared_width / 2, mat_left + prepared_height / 2)

            if click == 0:
                subprocess.Popen(f'adb -s {emulator_port} shell input tap {bottom_right[0]} {bottom_right[1]}')

            else:
                return bottom_right

    # 判斷模擬器狀況
    def device_screenshot(self):
        while 1:
            e_list = adb.device_list()
            # ======================================= 偵測所有模擬器頁面是否正常
            for em in e_list:
                self.emulator_png(em)
            time.sleep(5)

    #
    def emulator_png(self, em):
        # 按各模擬器截圖
        em_screenshot = self.screenshot(emulator_port=em.serial)

        # =============================================== 判斷是否會員過期 =========================================
        talk_expires1 = self.matchpng('talk_expires1', em_screenshot, 2, emulator_port=em.serial)
        talk_expires2 = self.matchpng('talk_expires2', em_screenshot, 2, emulator_port=em.serial)
        # ======= 判斷是否會員過期 =======
        game_over = self.matchpng('game_over2', em_screenshot, 2, emulator_port=em.serial)
        # ======= 判斷網頁是否正常1 =======
        star = self.matchpng('star', em_screenshot, 2, emulator_port=em.serial)
        # ======= 判斷網頁是否正常2 =======
        star1 = self.matchpng('star1', em_screenshot, 2, emulator_port=em.serial)
        if talk_expires1 or talk_expires2 or game_over or (star is None and star1 is None):
            self.go_m(em.serial, talk_expires1, talk_expires2, game_over, star, star1,)
            time.sleep(15)

    #
    def go_m(self, emulator_port, *arg):
        # =============================================== 判斷是否會員過期 =========================================
        tt1 = 1
        talk_expires1 = arg[0]
        talk_expires2 = arg[1]
        # ======= 判斷是否會員過期 =======
        game_over = arg[2]
        # ======= 判斷網頁是否正常1 =======
        star = arg[3]
        # ======= 判斷網頁是否正常2 =======
        star1 = arg[4]
        # if talk_expires1 or talk_expires2 or game_over or (star is None and star1 is None):
        notime = datetime.now().strftime('%Y%m%d%H%M%S')
        if game_over:
            print("桌次關閉!")
            tt1 = 60
        elif star is None and star1 is None:
            if star is None and star1 is None:
                print("桌次關閉-繼續等待!")
                tt1 = 10
            else:
                print(f"網頁有問題!")
                self.screenshot(save=1, pngname=f'/hhh{notime}')
                tt1 = 7
        else:
            print("會員過期!")
            tt1 = 1

        time.sleep(1)

        # 網頁重整
        self.go_stake(emulator_port=emulator_port, waitt=tt1)

    # 從首頁開啟browser，並輸入網址
    def go_stake(self, restart=0, emulator_port='', waitt=1):
        clickurl = f'adb -s {emulator_port} shell input tap 230 150'  # 網址列的座標
        url = 'https://stake.com/casino/games/evolution-stake-exclusive-roulette-1'
        go_url = f'adb -s {emulator_port} shell input text "{url}"'
        keycode_enter = f'adb -s {emulator_port} shell input keyevent KEYCODE_ENTER'

        subprocess.Popen(clickurl)
        time.sleep(1)

        # if restart == 1:
        subprocess.Popen(go_url)
        time.sleep(3)
        subprocess.Popen(keycode_enter)

        # 等待網頁完成即點擊進入遊戲
        i = 0
        while True:
            # 按各模擬器截圖
            em_screenshot = self.screenshot(emulator_port=emulator_port)
            m_result = self.matchpng('moneymode', em_screenshot, click=1, emulator_port=emulator_port)
            if m_result is not None:
                subprocess.Popen(f'adb -s {emulator_port} shell input tap {m_result[0]} {m_result[1]}')
                break
            else:
                time.sleep(0.2)

            if i == 100:
                break
            i += 1

        time.sleep(5)
        # 確認劇場模式
        subprocess.Popen(f'adb -s {emulator_port} shell input tap 60 1700')
        time.sleep(1)
        self.run_stop = 0
        time.sleep(waitt)

    # 押注
    def bet_chips(self, next_bet_list, eps):
        ep = adb.device_list()[eps].serial
        for b in next_bet_list:
            position_dict = self.element_position()
            bet = f'adb -s {ep} shell input tap {position_dict[int(b)][0]} {position_dict[int(b)][1]}'
            subprocess.Popen(bet)
            time.sleep(0.3)

    # 元素座標
    def element_position(self):
        position_dict = {
            'chips_x2': [1000, 1166],
            'chips': [1000, 1000],
            'chips_01': [968, 777],
            'chips_1': [777, 888],
            'chips_5': [688, 1017],
            'chips_100': [888, 1250],
            0: [600, 430],
            34: [400, 1530],
            35: [600, 1530],
            36: [800, 1530]
        }
        for a in range(1, 34):
            if a % 3 == 1:
                x = 400
            elif a % 3 == 2:
                x = 600
            else:
                x = 800

            # if a in [22, 23, 24]:
            #     y = 540 + ((a - 1) // 3) * 89
            # else:
            y = 535 + ((a - 1) // 3) * 90

            position_dict[a] = [x, y]

        return position_dict

    # 模擬器金額
    def balance(self, emulator_port=''):
        new_image = self.screenshot(emulator_port=emulator_port)
        image_bgr = im.fromarray(cv2.cvtColor(new_image, cv2.COLOR_RGB2BGR))
        cropped_image = image_bgr.crop((188, 1870, 360, 1910))

        ocr = ddddocr.DdddOcr()
        try:
            # # 驗証碼號碼
            res = ocr.classification(cropped_image).replace('o', '0').replace('O', '0').replace('a', '')
        except:
            res = '0'

        decimal = 100
        if '.' in res:
            decimal = 1

        ea = float(res) / decimal
        amount = round(ea, 2)

        return amount

    """ ------------------------------------------------------------------------------------------------------------ """

    # 多線程
    def threadbutton(self, param, args=()):
        thread_methods = {
            'start_bet': self.start_bet,
            'number_rank': self.number_rank,
            'test1': self.test1,
            'emulator_png': self.emulator_png,
            'bet_chips': self.bet_chips,
            'go_m': self.go_m,
            # 'all_rank': self.all_rank,
            'device_screenshot': self.device_screenshot,
            'start_bet_button': self.start_bet_button
        }
        if param in thread_methods:
            # 設置線程為守護線程，防止退出主線程時，子線程還在運行
            ptd = threading.Thread(target=thread_methods[param], args=args)
            ptd.setDaemon(True)
            ptd.start()

    # 錯誤通知
    def LineNotify(self, msg):
        # 修改為你的權杖內容
        token = '2zioQQiosb83U2io1VPfreb5vOdpygVNJX52fiSFKoF'
        headers = {
            "Authorization": "Bearer " + token,
            "Content-Type": "application/x-www-form-urlencoded"
        }
        payload = {'message': msg}
        r = requests.post("https://notify-api.line.me/api/notify", headers=headers, params=payload)
        return r.status_code

    #
    def start_bet_button(self):
        print(f"*** 開始執行!!!! ***")
        self.threadbutton('start_bet')

    # 讀取txt
    def read_txt(self, txt):
        with open(f'{txt}.txt', 'r') as file:
            # 读取文件内容
            file_contents = file.readlines()

        file.close()

        return file_contents

    # 測試內容
    def test1(self):
        startscript = ""  # 下載網頁資訊腳本所在資料夾
        strategyrf = open(startscript + 'param2.py', 'r', encoding='utf8')
        words = strategyrf.read()
        exec(words)
        strategyrf.close()

    # 主
    def __init__(self):
        self.file_path = os.path.realpath(__file__)  # 當前python執行檔的絕對路徑
        self.png_path = os.path.dirname(self.file_path) + '\\png'  # 當前資料夾 + png資料夾
        self.adb_path = os.path.dirname(self.file_path) + '\\Tool'  # 當前資料夾 + adb資料夾
        # 改變當前工作目錄到adb目標資料夾
        os.chdir(self.adb_path)

        self.window = tk.Tk()
        self.window.geometry('668x650+420+250')  # 視窗大小
        # self.window.resizable(0, 0)
        self.window.title('模擬下單-實際下單')  # 視窗名稱

        # ================== 連接MSSQL ==================
        login_info = self.read_txt('login_info')
        self.svn = login_info[0].strip()
        self.dtbn = login_info[1].strip()
        self.tbn = 'Roulette'
        self.uid = login_info[2].strip()
        self.pwd = login_info[3].strip()

        self.sql_server = MSSQL(self.svn, self.dtbn, self.uid, self.pwd)

        # ================== 參數 ==================
        self.pre_time_dict = {}  # 用以記錄每個下單上筆時間
        self.count_data = 0  # 記錄self.data key值
        self.mixed = []  # 500, 50的交集下單組數
        self.top_three = []  # 策略排名前三
        self.all_bets = {}  # 按模擬器分類所以要下單的號碼
        self.notify_info = {}

        # ================== 會員資料 ==================
        account_info = self.read_txt('account')
        self.account_name = account_info[0].strip()  # 會員名稱
        self.account_int = account_info[1].strip()  # 小數點
        self.account = account_info[2:]  # 所有參數

        # ================== tk ==================

        mt = ['歷史筆數', '自訂組數', 'Top', '號碼-+', '交集']
        self.bet_type = ttk.Combobox(self.window, value=mt, width=8, height=5, state='readonly')
        self.bet_type.current(0)

        self.up_var = tk.IntVar()
        up_checkbutton = tk.Checkbutton(self.window, text='上升', variable=self.up_var, onvalue=1, offvalue=0)
        self.up_var.set(1)

        self.bet_self = tk.Entry(self.window)
        self.bs = tk.Label(self.window, text='自訂組數:')
        self.bet_self.insert(0, self.account[1].strip())

        self.x2_var = tk.IntVar()
        c1 = tk.Checkbutton(self.window, text='X2', variable=self.x2_var, onvalue=1, offvalue=0)
        self.x2_var.set(self.account[5])

        self.c_error = tk.Entry(self.window)
        self.crc = tk.Label(self.window, text='連錯換單:')
        self.c_error.insert(0, '3')

        self.s_error = tk.Entry(self.window)
        self.src = tk.Label(self.window, text='二次換單:')
        self.s_error.insert(0, '2')

        # ======= Profit/Loss ======
        self.profit = tk.Entry(self.window)
        self.pro_p = tk.Label(self.window, text='%')
        self.profit.insert(0, '20')

        self.loss = tk.Entry(self.window)
        self.loss_p = tk.Label(self.window, text='%')
        self.loss.insert(0, '20')

        self.bet_history = tk.Entry(self.window)
        self.bh = tk.Label(self.window, text='歷史筆數:')
        self.bet_history.insert(0, '24')

        self.bet_count = tk.Entry(self.window)
        self.bc = tk.Label(self.window, text='下單組數(-+):')
        self.bet_count.insert(0, 5)

        self.bet_time = tk.Entry(self.window)
        self.bt = tk.Label(self.window, text='次後不再下注')
        self.bet_time.insert(0, 2)

        # ====== 起始Amount ======
        self.start_amount = tk.Entry(self.window)
        self.sa = tk.Label(self.window, text='起始金額:')
        self.start_amount.insert(0, '10000')

        # ====== 每單籌碼 ======
        self.chips = tk.Entry(self.window)
        self.cp = tk.Label(self.window, text='每單籌碼:')
        self.chips.insert(0, '0.1')

        # ====== 每單籌碼 ======
        self.changerank = tk.Entry(self.window)
        self.cr = tk.Label(self.window, text='更新排名:')
        self.changerank.insert(0, '1')

        self.hsrank = tk.Entry(self.window)
        self.hsrank.insert(0, '100')

        # ====== n筆內扣除 ======
        self.hs_deduct = tk.Entry(self.window)
        self.hs_deduct.insert(0, '11')
        self.hsd = tk.Label(self.window, text='內無則扣除:')
        self.first_reduce = tk.Entry(self.window)
        self.first_reduce.insert(0, '3')

        self.second_hsd = tk.Label(self.window, text='第二次無則扣除:')
        self.second_reduce = tk.Entry(self.window)
        self.second_reduce.insert(0, '0')

        # ===== 上升參數 =====
        self.up_profit = tk.Entry(self.window)
        self.up_profit.insert(0, '50')
        self.up_profit_label = tk.Label(self.window, text='上升獲利:')

        self.up_front = tk.Entry(self.window)
        self.up_front.insert(0, '19')
        self.up_front_label = tk.Label(self.window, text='往前:')

        self.up_later = tk.Entry(self.window)
        self.up_later.insert(0, '24')
        self.up_later_label = tk.Label(self.window, text='往後:')

        self.up_profit_label.place(x=300, y=100)
        self.up_profit.place(x=360, y=100, width=30, height=23)

        self.up_front_label.place(x=390, y=100)
        self.up_front.place(x=425, y=100, width=30, height=23)

        self.up_later_label.place(x=455, y=100)
        self.up_later.place(x=490, y=100, width=30, height=23)

        # ===== 設定是否下注 =====
        be = ['', '1', '2', '3', '4']
        self.be1 = tk.Label(self.window, text='模擬器:')
        self.bet_emulator = ttk.Combobox(self.window, value=be, width=8, height=5, state='readonly')
        self.bet_emulator.current(1)

        # === 新增/刪除 ===
        add_button = tk.Button(self.window, text="新增任務", command=self.add_task)
        delete_button = tk.Button(self.window, text="刪除任務", command=self.delete_task)
        update_button = tk.Button(self.window, text="更新任務", command=self.update_task)
        start_button = tk.Button(self.window, text="執行", command=self.start_bet_button)
        test = tk.Button(self.window, text='測試', command=self.test1)

        # 任务列表
        # === 任務列表 ===
        frame = tk.Frame(self.window)
        # 数据
        self.data = {}
        self.data1 = {'Bet_Type': None, 'Amount': None, 'Emulator': None, 'Number': None, 'High': None, 'Low': None}
        for i in range(1):
            self.data[i] = self.data1
        # 创建表格3
        self.table = TableCanvas(frame, data=self.data, width=588, height=200)
        # table.createTableFrame()
        self.table.show()

        # 任务列表2
        # === 任務列表 ===
        frame2 = tk.Frame(self.window)
        # 数据
        self.data2 = {}
        self.data22 = {'Bet_Type': None, 'Amount': None, 'Emulator': None, 'Number': None, 'High': None, 'Low': None}
        for i in range(1):
            self.data2[i] = self.data22
        # 创建表格3
        self.table2 = TableCanvas(frame2, data=self.data2, width=588, height=200)
        # table.createTableFrame()
        self.table2.show()

        # ================== tk位置編排 ==================

        # === 策略模式 ===
        self.bet_type.place(x=10, y=10)

        # === 上升選項 ===
        up_checkbutton.place(x=90, y=10)

        # === x2 ===
        c1.place(x=138, y=10)

        # === 自訂組數 ===
        self.bs.place(x=180, y=10)
        self.bet_self.place(x=238, y=10, width=120, height=23)

        # ===
        self.crc.place(x=358, y=10)
        self.c_error.place(x=418, y=10, width=30, height=23)

        self.src.place(x=358, y=40)
        self.s_error.place(x=418, y=40, width=30, height=23)

        # === Profit/Loss ===
        self.profit.place(x=478, y=10, width=30, height=23)
        self.pro_p.place(x=508, y=10)

        self.loss.place(x=478, y=40, width=30, height=23)
        self.loss_p.place(x=508, y=40)

        # === 歷史筆數 ===
        self.bet_history.place(x=72, y=40, width=30, height=23)
        self.bh.place(x=10, y=40)

        # === 下單組數 ===
        self.bet_count.place(x=192, y=40, width=30, height=23)
        self.bc.place(x=110, y=40)

        # === 幾次後不再下注 ===
        self.bet_time.place(x=232, y=40, width=30, height=23)
        self.bt.place(x=268, y=40)

        # === Amount/籌碼 ===
        self.start_amount.place(x=72, y=70, width=50, height=23)
        self.sa.place(x=10, y=70)
        self.chips.place(x=202, y=70, width=50, height=23)
        self.cp.place(x=140, y=70)

        # ===
        self.changerank.place(x=462, y=70, width=30, height=23)
        self.cr.place(x=400, y=70)
        self.hsrank.place(x=512, y=70, width=30, height=23)

        # === 下單機組 ===
        self.be1.place(x=268, y=70)
        self.bet_emulator.place(x=318, y=70)

        # ===
        self.hs_deduct.place(x=10, y=100, width=30, height=23)
        self.hsd.place(x=40, y=100)
        self.first_reduce.place(x=110, y=100, width=30, height=23)
        self.second_hsd.place(x=150, y=100)
        self.second_reduce.place(x=245, y=100, width=30, height=23)

        # === 新增/刪除 ===
        add_button.place(x=548, y=10)
        delete_button.place(x=548, y=40)
        update_button.place(x=548, y=70)
        start_button.place(x=548, y=100)
        #
        test.place(x=618, y=10)

        # === 任務列表 ===
        frame.place(x=7, y=130)

        # # === 任務列表2 ===
        frame2.place(x=7, y=390)

        self.window.mainloop()


Stake_Simulate()
