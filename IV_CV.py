import SQC_analysis_tools as sqc
import matplotlib.pyplot as plt
import glob as glob
import os
import argparse
import pandas as pd
import numpy as np
from matplotlib.backends.backend_pdf import PdfPages


color = ['red', 'blue', 'black', 'gold', 'purple', 'green', 'violet', 'peru', 'lightskyblue',
         'pink', 'slategray', 'lime', 'lightgreen', 'cyan', 'brown', 'darkcyan',  'lightgray', 'tan', 'thistle' ]


def iv_analysis(file):

     if 'HPK' in file:
         start_line = 23
         
     else:
         start_line = 9

     df = sqc.make_Dataframe_IVCV(file, start_line)

     voltage = df['Voltage [V]'].abs()
     current = (df['current [A]']*1e9).abs()
     
     
     return voltage, current


def vfd_analysis(file):


    if 'HPK' in file:
         start_line = 76
         
    else:
         start_line = 9

    df = sqc.make_Dataframe_IVCV(file, start_line)
    voltage = df['Voltage [V]'].abs()
    cap = df['capacitance [F]'].abs()
     
  
    c_inv = 1./cap**2
  
    return voltage, c_inv

 
  
  

def overlay_plots(folder, func, title, xlabel, ylabel):

    number = 0
    color_index =-1
    

    for file in folder:
       if 'IVC' in file:
         base = os.path.basename(file)
         lbl=os.path.splitext(base)[0]
         x,y = func(file)
         color_index +=1

         sqc.plot_graph(x, y, color[color_index], lbl, title, xlabel, ylabel)
         



def parse_args():

    parser = argparse.ArgumentParser(epilog = 'a path to directory containing ascii files to be analysed')
    parser.add_argument('path')
    return parser.parse_args()


def main():


    args = parse_args()

    filename = glob.glob(args.path + os.sep + '*.txt')

    with PdfPages('IVCV.pdf') as pdf:
    
      fig = plt.figure()
      overlay_plots(filename, iv_analysis, ' IV Curve', 'Voltage [V]', 'Current [nA]')
      pdf.savefig(fig)
         
      fig2 = plt.figure()
      overlay_plots(filename, vfd_analysis, 'Full Depletion Voltage', 'Voltage [V]', '1/C$^2$ [F$^{-2}$]')
      pdf.savefig(fig2)


if __name__ == "__main__":
    main()
