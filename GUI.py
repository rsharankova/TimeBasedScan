import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from scanner import scanner
from functions import *

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.backends.backend_tkagg import NavigationToolbar2Tk
from matplotlib.figure import Figure

import numpy as np
import os
import seaborn as sn
#import urllib.request

import subprocess
#import analysis


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
        
        get_ticket(userid,password)
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
        #self.geometry("635x400")
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
        self.matrix_data = None
        self.reference_data = None
        self.trajectory_data = None
        self.BPM_positions = {}
        self.FFT_data = None
        self.response_matrix_bpm = None
        self.response_df = None
        self.cavities = ['L:RFBPAH', 'L:V1QSET', 'L:V2QSET', 'L:V3QSET', 'L:V4QSET', 'L:V5QSET','L:RFQPAH']
        self.basis = None
        self.linear_coef = None
        self.pinv_coef = None
        self.fraction = 0.

        # Create the tab control
        self.tabControl = ttk.Notebook(self)

        # Create Tab1
        self.tab1 = ttk.Frame(self.tabControl)
        self.tab1.pack(expand=1)
        self.tabControl.add(self.tab1, text='Record Data')
        self.tabControl.pack(expand=1, fill="both")

        # Create Tab2
        self.tab2 = ttk.Frame(self.tabControl)
        self.tabControl.add(self.tab2, text='Response')
        self.tabControl.pack(expand=1, fill="both")

        # Create Tab3
        self.tab3 = ttk.Frame(self.tabControl)
        self.tabControl.add(self.tab3, text='Correction')
        self.tabControl.pack(expand=1, fill="both")
        
        # Add widgets to Tab1
        self.create_widgets_in_tab1()
        # Add widgets to Tab2
        self.create_widgets_in_tab2()
        # Add widgets to Tab3
        self.create_widgets_in_tab3()

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

        # Scan enable/disable
        scan_label = ttk.Label(self.tab1,text='Enable scan')
        scan_label.grid(column=2, row=4, columnspan=1, padx=1, pady=1)
        self.scan_select = ttk.Combobox(self.tab1,state='readonly',values =['Disable','Enable'])
        self.scan_select.current(0)
        self.scan_select.grid(column=2,row =5)
        
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

    def create_widgets_in_tab2(self):
        labels = ['Matrix File']

        for i, text in enumerate(labels):
            label = ttk.Label(self.tab2, text=text)
            label.grid(column=0, row=i, sticky='W', padx=5, pady=5)
            entry = ttk.Entry(self.tab2)
            entry.grid(column=1, row=i, sticky='EW', padx=5, pady=2)
            self.entries[text] = entry
            button = ttk.Button(self.tab2, text='Browse', command=lambda e=entry, t=text: self.browse(e, t))
            button.grid(column=2, row=i, sticky='W', padx=5, pady=2)


        # Button for reading setup file
        ref_button = ttk.Button(self.tab2, text="Load File", command=self.load_matrix_data)
        ref_button.grid(column=0, row=len(labels), columnspan=1, pady=1)

        # Button for data visualization
        plot_button = ttk.Button(self.tab2, text="Plot data", command=self.plot_data)
        plot_button.grid(column=1, row=len(labels), columnspan=1, pady=1)

        # Button for calculating matrix
        matrix_button = ttk.Button(self.tab2, text="Calculate Matrix", command=self.calc_matrix)
        self.plot_matrix_button = ttk.Button(self.tab2, text="Plot Matrix", command=self.plot_matrix)
        matrix_button.grid(column=2, row=len(labels), columnspan=1, pady=1)

        #Device selector for plotting
        self.devlist = ttk.Combobox(self.tab2,
            state="readonly",
            postcommand = self.updtcblist
        )
        #self.devlist.grid(column=0,row=3)

        #Time or freq selector for plotting
        self.timefreq = ttk.Combobox(self.tab2,state='readonly',values =['Time','Frequency'])
        self.timefreq.current(0)
        #self.timefreq.grid(column=1,row=3)

        self.vectabl = ttk.Combobox(self.tab2,state='readonly',values =['Vector','Matrix'])
        self.vectabl.current(0)

        self.vecmat_selector = ttk.Combobox(self.tab2,state='normal',values =['All','Orthogonal',''])
        self.vecmat_selector.current(0)

        self.select_button = ttk.Combobox(self.tab2,state='normal',values =['All','Orthogonal',''])
        self.select_button = ttk.Button(self.tab2, text="Select basis", command=self.select_b)
        
        #Frame for canvas
        frame = tk.Frame(self.tab2)
        frame.grid(column=0,row=4,columnspan=4,sticky='nsew')

        # Configure the grid layout
        self.tab2.rowconfigure(4, weight=1)
        self.tab2.columnconfigure(1, weight=1)

        #Figure
        self.fig = Figure(dpi=100)
        ax = self.fig.add_subplot(111)

        # Create a canvas and embed it in the frame
        self.canvas = FigureCanvasTkAgg(self.fig, master=frame)
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # Add a toolbar
        toolbar = NavigationToolbar2Tk(self.canvas, frame)
        toolbar.update()

        self.canvas.draw()

    def create_widgets_in_tab3(self):
        labels = ['Reference File','Trajectory File']

        for i, text in enumerate(labels):
            label = ttk.Label(self.tab3, text=text)
            label.grid(column=0, row=i, sticky='W', padx=5, pady=5)
            entry = ttk.Entry(self.tab3)
            entry.grid(column=1, row=i, sticky='EW', padx=5, pady=2)
            self.entries[text] = entry
            button = ttk.Button(self.tab3, text='Browse', command=lambda e=entry, t=text: self.browse(e, t))
            button.grid(column=2, row=i, sticky='W', padx=5, pady=2)


        # Button for reading setup file
        ref_button = ttk.Button(self.tab3, text="Load Files", command=self.load_trajectories)
        ref_button.grid(column=0, row=len(labels), columnspan=1, pady=1)

         # Button for data visualization
        #plot_button = ttk.Button(self.tab3, text="Plot trajectory", command=self.plot_trajectory)
        #plot_button.grid(column=1, row=len(labels), columnspan=1, pady=1) 

        # Button for linear fit
        linear_button = ttk.Button(self.tab3, text="Linear fit", command=self.linear_fit)
        linear_button.grid(column=1, row=len(labels), columnspan=1, pady=1) 

        # Button for Pseudoinverse
        pinv_button = ttk.Button(self.tab3, text="Pseudo inverse", command=self.pinv_fit)
        pinv_button.grid(column=2, row=len(labels), columnspan=1, pady=1) 

        frac_label = ttk.Label(self.tab3, text='Correction fraction')
        frac_label.grid(column=3, row=0, sticky='EW', padx=2, pady=5)
        self.frac_select = ttk.Entry(self.tab3)
        self.frac_select.grid(column=3, row=1, sticky='EW', padx=2, pady=2)
        
        # Button for Applying Settings
        set_button = ttk.Button(self.tab3, text="Apply corr.", command=self.apply_correction)
        set_button.grid(column=3, row=len(labels), columnspan=1, pady=1) 

        #Frame for canvas
        frame = tk.Frame(self.tab3)
        frame.grid(column=0,row=4,columnspan=4,sticky='nsew')

        # Configure the grid layout
        self.tab3.rowconfigure(4, weight=1)
        self.tab3.columnconfigure(0, weight=1)

        #Figure
        self.fig2 = Figure(dpi=100)
        ax = self.fig2.add_subplot(111)

        # Create a canvas and embed it in the frame
        self.canvas2 = FigureCanvasTkAgg(self.fig2, master=frame)
        self.canvas2.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # Add a toolbar
        toolbar = NavigationToolbar2Tk(self.canvas2, frame)
        toolbar.update()

        self.canvas2.draw()
    
    def plot_data(self):
        if not self.devlist.winfo_ismapped():
            self.devlist.grid(column=0,row=3)
            self.timefreq.grid(column=1,row=3)
        if self.vectabl.winfo_ismapped():
            self.vectabl.grid_remove()
            self.plot_matrix_button.grid_remove()
            self.vecmat_selector.grid_remove()
            self.select_button.grid_remove()
            
        self.fig.clf()
        
        if self.devlist.get() !='':
            if self.timefreq.get() == 'Time':
                self.fig.gca().plot(self.matrix_data[self.devlist.get()])
            else:
                self.FFT_data = apply_FFT([self.matrix_data])
                plot_fft(self.fig.gca(),self.FFT_data[0],[self.devlist.get()],299,4)
        else:
            pass
        self.canvas.draw()

    def plot_trajectory(self):
        self.fig2.clf()
        if self.trajectory_data is not None:
            self.fig2.gca().plot(list(self.BPM_positions.values()),
                                 self.trajectory_data.loc[list(self.BPM_positions.keys())])
        else:
            pass
        self.canvas2.draw()
        
    def login(self):
        LogWin = LoginDialog(self)

    def updtcblist(self):
        if self.matrix_data is not None:
            self.devlist['values'] =list(self.matrix_data.columns)
        else:
            pass

    def select_b(self):
        if self.vecmat_selector.get() =='All':
            self.basis = np.arange(len(self.cavities))
        elif self.vecmat_selector.get() =='Orthogonal':
            self.basis = select_basis(self.response_matrix_bpm)   
        else:
            self.basis = [ int(s.strip()) for s in self.vecmat_selector.get().split(',')]
        print(self.basis)
    
    def load_matrix_data(self):
        filename = self.entries['Matrix File'].get()
        print(filename)

        dataset = load_BPMphase_data_multi(self.cavities,[filename],[],scan=True)
        dataset = [df - df.mean() for df in dataset]
        
        self.BPM_positions = remove_noisy_bpm(dataset[0])
        self.matrix_data = dataset[0]

    def load_trajectories(self):
        filenames = [self.entries['Reference File'].get(),self.entries['Trajectory File'].get()]

        dataset = load_BPMphase_data_multi(self.cavities,filenames,[],scan=False)
        
        self.reference_data = dataset[0].mean()
        self.trajectory_data = (dataset[1] - dataset[0]).mean()
        
        bad_BPMs = self.trajectory_data.loc[abs(self.trajectory_data) >20.].index.tolist()
        self.BPM_positions = {x:self.BPM_positions[x] for x in self.BPM_positions if x not in bad_BPMs}

        self.plot_trajectory()
        
    def linear_fit(self):
        vec_list = [self.response_df.iloc[:,i].loc[list(self.BPM_positions.keys())] for i in self.basis]
        self.linear_coef = linear_fit_to_basis(self.trajectory_data.loc[list(self.BPM_positions.keys())],
                                                vec_list)
        self.fig2.clf()
        plot_fit_traj(self.fig2.gca(),self.cavities,self.trajectory_data, 
                      self.basis, self.response_df,
                      self.linear_coef,self.BPM_positions)
        self.canvas2.draw()

    def pinv_fit(self):
        self.pinv_coef = matrix_inversion(self.trajectory_data.loc[list(self.BPM_positions.keys())],
                                        self.response_df.iloc[:,list(self.basis)].loc[list(self.BPM_positions.keys())])
                                              
        print(['%s %.3f'%(self.cavities[b],self.pinv_coef[i]) for i,b in enumerate(self.basis)])
        self.fig2.clf()
        plot_fit_traj(self.fig2.gca(),self.cavities,self.trajectory_data, 
                      self.basis, self.response_df,
                      self.pinv_coef,self.BPM_positions)
        self.canvas2.draw()

    def calc_matrix(self):
        if self.devlist.winfo_ismapped():
            self.devlist.grid_remove()
            self.timefreq.grid_remove()

        if not self.vectabl.winfo_ismapped():
            self.vectabl.grid(column=0,row=3)
            self.plot_matrix_button.grid(column=1,row=3)
            self.vecmat_selector.grid(column=2,row=3)
            self.select_button.grid(column=3,row=3)

        filtered = apply_FFT_filter(self.matrix_data,self.cavities,list(self.BPM_positions.keys()),tolerance=0.0001)
        response_matrix = calc_response_matrix(filtered,self.cavities)
        self.response_matrix_bpm = [r[self.BPM_positions.keys()] for r in response_matrix]
        self.response_df = pd.DataFrame(self.response_matrix_bpm, index = self.cavities, columns = list(self.BPM_positions.keys())).T
        
        
    def plot_matrix(self):
        self.fig.clf()
                
        if self.vectabl.get()=='Vector':
            plot_basis_vectors(self.fig.gca(),self.response_matrix_bpm,list(self.BPM_positions.values()),
                           self.cavities,self.basis)
        else:
            sn.heatmap(self.response_df,ax = self.fig.gca())
        self.canvas.draw()

    def apply_correction(self):
        if self.frac_select.get() !='':
            self.fraction = float(self.frac_select.get().strip())
        else:
            self.fraction = 0.
    
        devs = [self.cavities[b] for b in self.basis]
        nominals = self.sc.get_settings_once(devs)

        coef = np.zeros(len(devs))
        if self.linear_coef is not None and self.pinv_coef is None:
            coef = self.linear_coef
        elif self.pinv_coef is not None:
            coef = self.pinv_coef
        else:
            print('No coefficients')

        print('Nominals')
        print(['%s %.3f'%(d,nominals[i]) for i,d in enumerate(devs)])        
        print('Applying the following corrections')            
        print(['%s %.3f'%(d,self.fraction*coef[i]) for i,d in enumerate(devs)])

        
        self.role = self.selector.get()
        print(self.role)

        self.sc.apply_settings_once(devs,np.add(nominals,coef*self.fraction),self.role)
        time.sleep(1.5)
        print(self.sc.get_settings_once(devs))
        
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
        else:
            filename = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv")])
            if filename:
                entry_widget.delete(0, tk.END)
                entry_widget.insert(0, filename)
                self.workdir = os.path.dirname(filename)
            

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

        timestr = time.strftime("%Y%m%d_%H%M%S")
        setup_file_path = os.path.join(self.workdir, 'Setup_%s.csv'%timestr)
        with open(setup_file_path, 'w') as setup_file:
            for label, entry in self.entries.items():
                setup_file.write(f"{label},{entry.get()}\n")

            ramplist_filepath = self.generate_corrector_files()
            setup_file.write(f"Ramplist File,{ramplist_filepath}\n")

        messagebox.showinfo("Success", "The data has been written to Setup_%s.csv and ramp file has been generated."%timestr)

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
        elif self.scan_select.get()=='Disable':
            self.ramplist = []
            print('Scan disabled - will only read devices')


        self.role = self.selector.get()
        print(self.role)
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
