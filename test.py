# -*- coding: utf-8 -*-
from Tkinter import *

from ScrolledText import ScrolledText


def setLobbyUI(self):
    self['bg'] = '#708090'
    self.title('VV聊天大厅')
    # self.geometry(windows_center(830, 600, self.winfo_screenwidth(), self.winfo_screenheight()))
    self.press_send = False
    self.frame_left_top = Frame(self, width=650, height=460)
    self.frame_left_top.grid(row=0, column=0, padx=2, pady=2)
    self.frame_left_top.grid_propagate(0)
    self.text_msglist = ScrolledText(self.frame_left_top, borderwidth=1, highlightthickness=0,
                                     relief='flat', bg='#fffff0')
    self.text_msglist.tag_config('myTitle', foreground='#008B00', justify='right', font=("Times, 11"))
    self.text_msglist.tag_config('myContent', justify='right', font=("Courier, 11"))
    self.text_msglist.tag_config('otherTitle', foreground='blue', justify='left', font=("Times, 11"))
    self.text_msglist.tag_config('otherContent', justify='left', font=("Courier, 11"))
    self.text_msglist.tag_config('notice', foreground='gray', justify='center', font=("Times, 9"))
    self.text_msglist.place(x=0, y=0, width=650, height=460)

    self.frame_left_center = Frame(self, width=650, height=100)
    self.frame_left_center.grid(row=1, column=0, padx=2, pady=2)
    self.text_msg = Text(self.frame_left_center, highlightthickness=0, relief='flat', bg='#fffff0')
    self.text_msg.place(x=0, y=0, width=650, height=100)
    # self.text_msg.grid(sticky='WE')
    # self.text_msg.bind('<Shift-Return>', self.sendMsg)
    # self.text_msg.bind('<KeyRelease-Return>', self.clearMsg)

    self.frame_left_bottom = Frame(self, width=650, height=30, bg='#708090')
    self.frame_left_bottom.grid(row=2, column=0)
    self.frame_left_bottom.grid_propagate(0)
    self.send_msg_btn = Button(self.frame_left_bottom, text='发送')
    # self.send_msg_btn.bind('<Button-1>', self.sendMsg)
    # self.send_msg_btn.bind('<ButtonRelease-1>', self.clearMsg)
    self.send_msg_btn.place(x=540, y=2, height=23, width=110)
    self.send_msg_label = Label(self.frame_left_bottom, text='', fg='white', bg='#708090')
    self.send_msg_label.place(x=10, y=5, height=20, width=200)

    self.frame_right = Frame(width=180, height=600, bg='#708090')
    self.frame_right.grid(row=0, column=1, rowspan=3)
    self.frame_right.grid_propagate(0)
    self.time_label = Label(self.frame_right, bg='gray', justify='left')
    self.time_label.place(x=0, y=0, width=180)
    self.tip_label = Label(self.frame_right, justify='left', text='大厅用户 (0)', bg='#708090', fg='#fffafa')
    self.tip_label.place(x=50, y=100)
    self.user_list = StringVar()
    self.user_list_box = Listbox(self.frame_right, borderwidth=1, highlightthickness=0,
                                 relief='flat', bg='#ededed', listvariable=self.user_list)
    self.user_list_box.place(x=5, y=125, height=470, width=165)
    # self.user_list_box.bind('<Double-Button-1>', self.privateChat)
    # GlobalVal.sockt.send('09', '')
    self.add_room_btn = Button(self.frame_right, text='创建房间')
    self.add_room_btn.place(x=15, y=65)
    self.enter_room_btn = Button(self.frame_right, text='加入房间')
    self.enter_room_btn.place(x=100, y=65)



if __name__ == '__main__':
    root = Tk()
    setLobbyUI(root)
    root.mainloop()