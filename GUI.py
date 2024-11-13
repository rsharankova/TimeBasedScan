import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from scanner import scanner

import numpy as np
import os
#import urllib.request

import subprocess
import analysis


class LoginDialog(tk.Toplevel, object):
    def __init__(self,parent):
        super().__init__(parent)
        self.title("Login")
        self.parent=parent

        # Create and place the username label and entry
        self.username_label = tk.Label(self, text="Userid:")
        self.username_label.pack()
        
        self.username_entry = tk.Entry(self)
        self.username_entry.pack()
        
        # Create and place the password label and entry
        self.password_label = tk.Label(self, text="Password:")
        self.password_label.pack()
        
        self.password_entry = tk.Entry(self, show="*")  # Show asterisks for password
        self.password_entry.pack()
        
        # Create and place the login button
        self.login_button = tk.Button(self, text="Login", command=self.validate_login)
        self.login_button.pack()

    def validate_login(self):
        userid = self.username_entry.get()
        password = self.password_entry.get()
        
        # Check for ticket
        has_ticket = subprocess.call(['klist', '-s'])
        if not has_ticket:
            subprocess.call(['kdestroy'])
        
        analysis.get_ticket(userid,password)
        has_ticket = subprocess.call(['klist', '-s'])
        if not has_ticket:
            messagebox.showinfo(message="Login Successful")
            self.destroy()
        else:
            messagebox.showerror(message="Login Failed")


class SchedulerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Scheduler App")
        self.geometry("635x400")
        self.entries = {}
        self.options = ['testing','linac_trims','linac_quads','linac_daily_rf_tuning','400MeV_trims']
        self.selector = tk.StringVar()
        self.selector.set(self.options[0])
        self.role = self.selector.get()
        self.sc = scanner()
        self.Nmeas = 1
        self.workdir = os.getcwd()
        self.ramplist = []
        self.thread = ''


        # Create the tab control
        #self.tabControl = ttk.Notebook(self)

        # Create Tab1
        #self.tab1 = ttk.Frame(self.tabControl)
        self.tab1 = ttk.Frame(self)
        self.tab1.pack(expand=1)
        #self.tabControl.add(self.tab1, text='Input Parameters')
        #self.tabControl.pack(expand=1, fill="both")

        # Create Tab2
        #self.tab2 = ttk.Frame(self.tabControl)
        #self.tabControl.add(self.tab2, text='Response')

        # Add widgets to Tab1
        self.create_widgets_in_tab1()

    def create_widgets_in_tab1(self):
        labels = ['Reading Devices File',
                  'Device List', 'Nominals','Amplitude', 
                  'Number of Periods', 'Points per Superperiod','Number of Superperiods', 'Sampling Event','Number of Measurements']

        for i, text in enumerate(labels):
            label = ttk.Label(self.tab1, text=text)
            label.grid(column=0, row=i, sticky='W', padx=5, pady=5)
            entry = ttk.Entry(self.tab1)
            entry.grid(column=1, row=i, sticky='EW', padx=5, pady=2)
            self.entries[text] = entry
            if text in ['Reading Devices File']:
                button = ttk.Button(self.tab1, text='Browse', command=lambda e=entry, t=text: self.browse(e, t))
                button.grid(column=2, row=i, sticky='W', padx=5, pady=2)
            if text.find('Nominals')!=-1:
                button = ttk.Button(self.tab1, text='Fetch', command= lambda: self.fetch_nominals())
                button.grid(column=2, row=i, sticky='W', padx=5, pady=2)
            if text.find('Measurements')!=-1:
                self.entries[text].delete(0,tk.END)
                self.entries[text].insert(0,'%d'%self.Nmeas)

                
        # Button for reading setup file
        read_button = ttk.Button(self.tab1, text="READ SETUP FILE", command=self.read_setup_file)
        read_button.grid(column=0, row=len(labels), columnspan=1, pady=1)

        # Button for generating setup file
        generate_button = ttk.Button(self.tab1, text="GENERATE SETUP FILE", command=self.write_to_setup_file)
        generate_button.grid(column=1, row=len(labels), columnspan=1, pady=1)

        # Setting role label
        label = ttk.Label(self.tab1,text='Setting role')
        label.grid(column=2, row=len(labels), columnspan=1, padx=1, pady=1)

        # Setting role selector
        setting_role = ttk.OptionMenu( self.tab1, self.selector , *self.options )
        setting_role.grid(column=2, row = len(labels)+1, columnspan=1, pady=1)
        setting_role.config(width=12)
        
        # Button to authenticate
        login_button = ttk.Button(self.tab1, text="LOGIN", command=self.login)
        login_button.grid(column=2, row=len(labels)+2, columnspan=1, pady=1)

        # Button to start scan
        start_scan_button = ttk.Button(self.tab1, text="START SCAN", command=self.start_scan)
        start_scan_button.grid(column=0, row=len(labels)+1, columnspan=1, pady=1)

        # Button to abort scan
        stop_scan_button = ttk.Button(self.tab1, text="STOP SCAN", command=self.stop_scan)
        stop_scan_button.grid(column=0, row=len(labels)+2, columnspan=1, pady=1)

        # Button to pause scan
        pause_scan_button = ttk.Button(self.tab1, text="PAUSE SCAN", command=self.pause_scan)
        pause_scan_button.grid(column=1, row=len(labels)+1, columnspan=1, pady=1)

        # Button to resume scan
        resume_scan_button = ttk.Button(self.tab1, text="RESUME SCAN", command=self.resume_scan)
        resume_scan_button.grid(column=1, row=len(labels)+2, columnspan=1, pady=1)

        
        # Configure the grid layout
        self.tab1.columnconfigure(1, weight=1)

    def login(self):
        LogWin = LoginDialog(self)
        
        
    def browse(self, entry_widget, text):
        if text == 'Reading Devices File':
            filename = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv")])
            if filename:
                entry_widget.delete(0, tk.END)
                entry_widget.insert(0, filename)
                self.workdir = os.path.dirname(filename)
            
        elif text == 'Output File Path':
            directory = filedialog.askdirectory()
            if directory:
                entry_widget.delete(0, tk.END)
                entry_widget.insert(0, directory)
        

    def read_setup_file(self):
        filename = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv")])
        config = []
        if filename:
            config = [line.strip().split(',') for line in open(filename).readlines()]
            self.workdir = os.path.dirname(filename)        
        # Format:
        #0 Reading deivices file
        #1 Ramp list file
        #2 Device list
        #3 Nominals
        #4 Amplitude
        #5 Number of periods
        #6 Points per superperiod
        #7 Number of superperiods
        #8 Sampling event
        #9 Number of measurements 
        
        for c in config:
            if c[0].find('Device List')!=-1:
                self.entries['Device List'].delete(0,tk.END)
                self.entries['Device List'].insert(0,','.join(map(str,c[1:])))
            elif c[0].find('Amplitude')!=-1:
                self.entries['Amplitude'].delete(0,tk.END)
                self.entries['Amplitude'].insert(0,','.join(map(str,c[1:])))
            elif c[0].find('Number of Periods')!=-1:
                self.entries['Number of Periods'].delete(0,tk.END)
                self.entries['Number of Periods'].insert(0,','.join(map(str,c[1:])))
            elif c[0].find('Number of Superperiods')!=-1:
                self.entries['Number of Superperiods'].delete(0,tk.END)
                self.entries['Number of Superperiods'].insert(0,','.join(map(str,c[1:])))
            elif c[0].find('Points per Superperiod')!=-1:
                self.entries['Points per Superperiod'].delete(0,tk.END)
                self.entries['Points per Superperiod'].insert(0,','.join(map(str,c[1:])))
            elif c[0].find('Reading')!=-1:
                self.entries['Reading Devices File'].delete(0,tk.END)
                self.entries['Reading Devices File'].insert(0,','.join(map(str,c[1:])))
            elif c[0].find('Sampling')!=-1:
                self.entries['Sampling Event'].delete(0,tk.END)
                self.entries['Sampling Event'].insert(0,','.join(map(str,c[1:])))
            elif c[0].find('Nominal')!=-1:
                self.entries['Nominals'].delete(0,tk.END)
                self.entries['Nominals'].insert(0,','.join(map(str,c[1:])))
            elif c[0].find('Ramplist File')!=-1:
                self.load_ramplist(c[1])
            elif c[0].find('Number of Measurements')!=-1:
                self.entries['Number of Measurements'].delete(0,tk.END)
                self.entries['Number of Measurements'].insert(0,','.join(map(str,c[1:])))

            else:
                print('Found unknown configuration item',c[0])


    def fetch_nominals(self):
        devs = [name.strip() for name in self.entries['Device List'].get().split(',') if name!='']
        if len(devs)>0 and devs[0]=='':
            print('Device list empty')
            return

        nominals = self.sc.get_settings_once(devs)
        '''
        nominals = []
        for dev in devs:
            url="https://www-ad.fnal.gov/cgi-bin/acl.pl?acl=read+%s"%(dev.replace(':','_'))
            response = urllib.request.urlopen(url)
            html_data = response.read().decode("utf-8").strip()
            nominals.append(html_data.split()[-2])
        '''    
        self.entries['Nominals'].delete(0,tk.END)
        self.entries['Nominals'].insert(0,','.join(map(str,nominals)))
        
        
    def write_to_setup_file(self):

        setup_file_path = os.path.join(self.workdir, 'Setup.csv')
        with open(setup_file_path, 'w') as setup_file:
            for label, entry in self.entries.items():
                setup_file.write(f"{label},{entry.get()}\n")

            ramplist_filepath = self.generate_corrector_files()
            setup_file.write(f"Ramplist File,{ramplist_filepath}\n")

        messagebox.showinfo("Success", "The data has been written to Setup.csv and ramp file has been generated.")

    def load_ramplist(self,rampfile):
        try:
            rampdata = open(rampfile).readlines()
        except:
            print('Cannot open ramp file')
            return
            
        for line in rampdata:
            if line.strip().startswith('//'):
                continue
            elif line=='':
                continue
            else:
                ll = line.strip().split(',')
                devs = [l for l in ll if l.find(':')!=-1]
                vals = [float(l) for l in ll[1:] if l not in devs]
                tmplist=[ll[0]]
                [tmplist.extend(list(a)) for a in zip(devs,vals)]
                self.ramplist.append(tmplist)


    def stop_scan(self):
        if self.thread in self.sc.get_list_of_threads():            
            self.sc.stop_thread('%s'%self.thread)


    def pause_scan(self):
        if self.thread in self.sc.get_list_of_threads():
            self.sc.pause_thread('%s'%self.thread)

    def resume_scan(self):
        if self.thread in self.sc.get_list_of_threads():
            self.sc.resume_thread('%s'%self.thread)


    def start_scan(self):
        if self.ramplist == []:
            print('No ramp list loaded - will only read devices')


        self.role = self.selector.get()
        evt = '@e,%s,e,0'%(self.entries['Sampling Event'].get().strip().split(',')[0])
        devs = [s for s in self.ramplist[0] if str(s).find(':')!=-1] if len(self.ramplist)>0 else[]
        read_list = self.sc.readList(self.entries['Reading Devices File'].get().strip().split(',')[0])
        read_list  = [d for d in devs if d not in read_list] + read_list
        
        self.Nmeas= int(self.entries['Number of Measurements'].get().strip())
        print(self.Nmeas)

        set_list = ['%s%s'%(s.replace(':','_'),evt) for s in devs]

        drf_list = set_list+['%s%s'%(l,evt) for l in read_list if len(read_list)!=0]
            
        self.thread = 'scan'

        timeout = 120 #2 min

        try:
            self.sc.start_thread('%s'%self.thread,timeout,drf_list,self.ramplist,self.role,self.Nmeas)
        
        except Exception as e:
            print('Scan failed',e)

        
    def generate_corrector_files(self):
        self.ramplist = []
        
        device_names = [name.strip() for name in self.entries['Device List'].get().strip().split(',') if name!='']
        nominal_values = [float(val) for val in self.entries['Nominals'].get().strip().split(',') if val!='']
        amplitude_values = [float(val) for val in self.entries['Amplitude'].get().strip().split(',') if val!='']
        total_number_of_steps_list = [int(val) for val in self.entries['Points per Superperiod'].get().strip().split(',') if val!='']
        number_of_points_per_period =np.divide(total_number_of_steps_list[0], [int(val) for val in self.entries['Number of Periods'].get().strip().split(',') if val!=''])
        number_of_superperiods =[int(val) for val in self.entries['Number of Superperiods'].get().strip().split(',')]
        
        if not (len(device_names) == len(nominal_values) == len(amplitude_values) == len(number_of_points_per_period)):
            messagebox.showerror("Error", "The number of entries in each field must match.")
            print(len(device_names),len(nominal_values),len(amplitude_values),len(number_of_points_per_period))
            print(device_names,nominal_values,amplitude_values,number_of_points_per_period)
            return

        filepath = os.path.join(self.workdir, "%s.csv"%('_'.join([dev.split(':')[-1] for dev in device_names])))
                
        total_number_of_steps = total_number_of_steps_list[0]*number_of_superperiods[0]
        with open(filepath, 'w') as file:
            for step in range(total_number_of_steps):
                line = []
                if step==0:
                    line.append('0')
                else:
                    line.append('1')
                for i, d in enumerate(device_names):
                    value = nominal_values[i] + amplitude_values[i] * np.sin(2 * np.pi * (step / number_of_points_per_period[i]))
                    line.append(d)
                    line.append(float(value))
                file.write(f"%s\n"%','.join(map(str,line)))
                self.ramplist.append(line)


        return(filepath)
    
if __name__ == "__main__":
    app = SchedulerApp()
    app.mainloop()
