import sys
import json
import html
from pathlib import Path
import numpy as np
import pandas as pd
from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex, QTranslator, QLibraryInfo
from PySide6.QtGui import QAction, QKeySequence, QTextDocument
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTableView, QTableWidget, QTableWidgetItem, QTabWidget, QTextBrowser, QFileDialog, QMessageBox, QPushButton, QDialog, QDialogButtonBox, QComboBox, QListWidget, QLabel, QAbstractItemView, QInputDialog)
from PySide6.QtPrintSupport import QPrinter
from matplotlib import rcParams
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from .data import Dataset, Variable
from .analysis import analyze, METHODS

rcParams['font.sans-serif'] = ['PingFang SC', 'Arial Unicode MS', 'Heiti SC', 'DejaVu Sans']
rcParams['axes.unicode_minus'] = False

class FrameModel(QAbstractTableModel):
    def __init__(self, dataset, changed=None):
        super().__init__()
        self.dataset = dataset
        self.changed = changed or (lambda:None)
    def rowCount(self,parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.dataset.frame)
    def columnCount(self,parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.dataset.frame.columns)
    def data(self,index,role=Qt.DisplayRole):
        if index.isValid() and role in (Qt.DisplayRole, Qt.EditRole):
            v=self.dataset.frame.iat[index.row(),index.column()]
            return '' if pd.isna(v) else str(v)
    def headerData(self,section,orientation,role=Qt.DisplayRole):
        if role==Qt.DisplayRole:
            return str(self.dataset.frame.columns[section]) if orientation==Qt.Horizontal else str(section+1)
    def flags(self,index):
        return super().flags(index)|Qt.ItemIsEditable
    def setData(self,index,value,role=Qt.EditRole):
        if role!=Qt.EditRole or not index.isValid():
            return False
        c=self.dataset.frame.columns[index.column()]
        try:
            if self.dataset.variables[c].kind=='数值':
                value=float(value) if str(value).strip() else np.nan
            else:
                value=str(value) if str(value) else np.nan
            self.dataset.frame.iat[index.row(),index.column()]=value
        except (ValueError,TypeError):
            return False
        self.dataChanged.emit(index,index)
        self.changed()
        return True

def tables_html(results):
    text='<html><head><meta charset="utf-8"><style>body{font-family:"PingFang SC",sans-serif}table{border-collapse:collapse}th,td{border:1px solid #888;padding:6px}h2{color:#287baf}</style></head><body><h1>StatMate 分析报告</h1><p>双侧检验；缺失值按分析排除。p 值以原始精度导出，极小值可显示为科学计数法。</p>'
    for name,frame in results.items():
        text+=f'<h2>{html.escape(name)}</h2>'+frame.to_html(index=False,border=0,float_format=lambda x:format(x,'.8g'))
    return text+'</body></html>'

class Window(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('StatMate — 免费中文统计分析')
        self.resize(1150,760)
        self.dataset=Dataset()
        self.results={}
        self.dirty=False
        self.tabs=QTabWidget()
        self.setCentralWidget(self.tabs)
        self.data_view=QTableView()
        self.variable_view=QTableWidget()
        self.report=QTextBrowser()
        self.figure=Figure(figsize=(8,5),layout='constrained')
        self.canvas=FigureCanvasQTAgg(self.figure)
        for widget,name in [(self.data_view,'数据视图'),(self.variable_view,'变量视图'),(self.report,'分析结果'),(self.canvas,'图表')]:
            self.tabs.addTab(widget,name)
        self.variable_view.itemChanged.connect(self.variable_changed)
        menu=self.menuBar().addMenu('文件')
        for title,shortcut,callback in [('导入数据…','Ctrl+O',self.import_data),('保存数据…','Ctrl+S',self.save_data),('导出分析结果…','Ctrl+Shift+S',self.export_results),('导出图表…',None,self.export_chart)]:
            self.action(menu,title,shortcut,callback)
        edit=self.menuBar().addMenu('数据')
        self.action(edit,'添加变量…',None,self.add_variable)
        self.action(edit,'添加观测',None,self.add_row)
        analysis_menu=self.menuBar().addMenu('分析')
        self.action(analysis_menu,'选择统计分析…','Ctrl+R',self.analysis_dialog)
        self.action(analysis_menu,'绘制直方图…',None,self.plot)
        help_menu=self.menuBar().addMenu('帮助')
        self.action(help_menu,'关于 StatMate',None,lambda:QMessageBox.about(self,'关于 StatMate','StatMate 0.1.0\n免费开源中文统计分析软件（MIT）\n分析结果请结合课程要求解释。'))
        self.refresh()
        self.statusBar().showMessage('欢迎使用 StatMate：通过“文件 → 导入数据”开始，或添加变量与观测。')
    def action(self,menu,title,shortcut,callback):
        a=QAction(title,self)
        if shortcut:a.setShortcut(QKeySequence(shortcut))
        a.triggered.connect(callback)
        menu.addAction(a)
    def error(self,e):
        QMessageBox.warning(self,'操作未完成',str(e))
    def mark_dirty(self):
        self.dirty=True
        self.setWindowModified(True)
    def refresh(self):
        self.model=FrameModel(self.dataset,self.mark_dirty)
        self.data_view.setModel(self.model)
        self.variable_view.blockSignals(True)
        self.variable_view.setColumnCount(7)
        self.variable_view.setHorizontalHeaderLabels(['名称','类型（数值/文本）','变量标签','值标签（JSON）','缺失值（JSON数组）','测量水平（名义/有序/尺度）','有效数'])
        self.variable_view.setRowCount(len(self.dataset.variables))
        for row,(name,v) in enumerate(self.dataset.variables.items()):
            for col,value in enumerate([name,v.kind,v.label,json.dumps(v.values,ensure_ascii=False),json.dumps(v.missing,ensure_ascii=False),v.measure,str(self.dataset.frame[name].count())]):
                item=QTableWidgetItem(value)
                if col in (0,6):item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.variable_view.setItem(row,col,item)
        self.variable_view.resizeColumnsToContents()
        self.variable_view.blockSignals(False)
    def variable_changed(self,item):
        c=list(self.dataset.variables)[item.row()]
        v=self.dataset.variables[c]
        value=item.text()
        try:
            if item.column()==1:
                if value not in ('数值','文本'):raise ValueError('类型只能为数值或文本')
                series=self.dataset.frame[c]
                converted=pd.to_numeric(series,errors='raise').astype(float) if value=='数值' else series.map(lambda x:str(x) if pd.notna(x) else np.nan).astype(object)
                self.dataset.frame[c]=converted
                v.kind=value
            elif item.column()==2:v.label=value
            elif item.column()==3:
                labels=json.loads(value)
                if not isinstance(labels,dict) or any(not isinstance(x,str) for x in labels.values()):raise ValueError('值标签格式示例：{"1":"男","2":"女"}')
                v.values={float(k) if v.kind=='数值' else k:label for k,label in labels.items()}
            elif item.column()==4:
                missing=json.loads(value)
                if not isinstance(missing,list) or any(not isinstance(x,(int,float,str)) for x in missing):raise ValueError('缺失值示例：[99, 999]')
                v.missing=[float(x) for x in missing] if v.kind=='数值' else [str(x) for x in missing]
            elif item.column()==5:
                if value not in ('名义','有序','尺度'):raise ValueError('测量水平必须为名义、有序或尺度')
                v.measure=value
            self.mark_dirty()
        except Exception as e:self.error(e)
        self.refresh()
    def confirm_discard(self):
        return not self.dirty or QMessageBox.question(self,'尚未保存','数据或变量设置尚未保存，是否放弃更改？',QMessageBox.Yes|QMessageBox.No,QMessageBox.No)==QMessageBox.Yes
    def import_data(self):
        if not self.confirm_discard():return
        path,_=QFileDialog.getOpenFileName(self,'导入数据','','数据文件 (*.sav *.xls *.xlsx *.csv *.txt)')
        if not path:return
        try:
            loaded=Dataset.load(path)
            self.dataset=loaded
            self.dirty=False
            self.results={}
            self.report.clear()
            self.figure.clear()
            self.canvas.draw()
            self.refresh()
            self.statusBar().showMessage(f'{Path(path).name}：{len(loaded.frame)} 个观测，{len(loaded.frame.columns)} 个变量；Excel 默认读取第一张工作表')
        except Exception as e:self.error(e)
    def save_data(self):
        path,_=QFileDialog.getSaveFileName(self,'保存数据（SAV 保留变量设置）','数据.sav','SPSS 数据 (*.sav);;Excel (*.xlsx);;CSV (*.csv)')
        if path:
            try:
                self.dataset.save(path)
                self.dirty=False
                self.statusBar().showMessage('数据已保存；CSV/Excel 仅保留数据，SAV 保留变量设置')
            except Exception as e:self.error(e)
    def add_variable(self):
        name,ok=QInputDialog.getText(self,'添加变量','变量名（建议使用英文字母开头）：')
        if ok and name:
            if name in self.dataset.variables:
                self.error('变量名已存在');return
            self.dataset.frame[name]=pd.Series(np.nan,index=self.dataset.frame.index,dtype=float)
            self.dataset.variables[name]=Variable()
            self.mark_dirty()
            self.refresh()
    def add_row(self):
        if not self.dataset.variables:
            self.error('请先添加变量');return
        self.dataset.frame.loc[len(self.dataset.frame)]=[np.nan]*len(self.dataset.variables)
        self.mark_dirty()
        self.refresh()
    def select_columns(self,title,multiple=True):
        d=QDialog(self)
        d.setWindowTitle(title)
        layout=QVBoxLayout(d)
        layout.addWidget(QLabel('变量按列表顺序使用。分组分析：数值变量在前，分组变量在后；\n配对/交叉表：前两项；回归：首项为因变量，其余为自变量。\n如需调整顺序，可在下方移动变量。'))
        picker=QListWidget()
        picker.addItems(list(self.dataset.variables))
        picker.setSelectionMode(QAbstractItemView.MultiSelection if multiple else QAbstractItemView.SingleSelection)
        picker.setDragDropMode(QAbstractItemView.InternalMove)
        layout.addWidget(picker)
        buttons=QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText('运行')
        buttons.button(QDialogButtonBox.Cancel).setText('取消')
        buttons.accepted.connect(d.accept)
        buttons.rejected.connect(d.reject)
        layout.addWidget(buttons)
        return [picker.item(i).text() for i in range(picker.count()) if picker.item(i).isSelected()] if d.exec()==QDialog.Accepted else []
    def analysis_dialog(self):
        method,ok=QInputDialog.getItem(self,'统计分析','选择分析方法：',METHODS,0,False)
        if not ok:return
        columns=self.select_columns(method)
        if not columns:return
        try:
            if method in METHODS[2:6] and len(columns)!=2:raise ValueError('该方法请恰好选择两个变量')
            tables=analyze(self.dataset.clean(),method,columns)
            number=len(self.results)+1
            for name,table in tables.items():self.results[f'{number}. {name}（{", ".join(columns)}）']=table
            self.report.setHtml(tables_html(self.results))
            self.tabs.setCurrentIndex(2)
        except Exception as e:self.error(e)
    def export_results(self):
        if not self.results:
            self.error('请先运行统计分析');return
        path,_=QFileDialog.getSaveFileName(self,'导出分析结果','分析结果.xlsx','Excel (*.xlsx);;CSV (*.csv);;PDF (*.pdf)')
        if not path:return
        try:
            export_results(self.results,path)
            self.statusBar().showMessage('分析结果已导出：'+path)
        except Exception as e:self.error(e)
    def plot(self):
        columns=self.select_columns('选择直方图变量',False)
        if not columns:return
        try:
            s=self.dataset.clean()[columns[0]]
            if not pd.api.types.is_numeric_dtype(s):raise ValueError('直方图需要数值变量')
            s=s.dropna()
            if s.empty or not np.isfinite(s).all():raise ValueError('需要有限数值观测')
            self.figure.clear()
            ax=self.figure.add_subplot(111)
            ax.hist(s,bins='auto',color='#4388bd',edgecolor='white')
            ax.set(title=columns[0]+' 分布',xlabel=columns[0],ylabel='频数')
            self.canvas.draw()
            self.tabs.setCurrentIndex(3)
        except Exception as e:self.error(e)
    def export_chart(self):
        if not self.figure.axes:
            self.error('请先绘制图表');return
        path,_=QFileDialog.getSaveFileName(self,'导出图表','图表.pdf','PDF (*.pdf);;PNG (*.png)')
        if path:
            try:self.figure.savefig(path,dpi=180)
            except Exception as e:self.error(e)
    def closeEvent(self,event):
        event.accept() if self.confirm_discard() else event.ignore()

def export_results(results,path):
    ext=Path(path).suffix.lower()
    if ext=='.xlsx':
        with pd.ExcelWriter(path,engine='openpyxl') as writer:
            for i,(name,frame) in enumerate(results.items(),1):
                pd.DataFrame({'分析':[name]}).to_excel(writer,sheet_name=f'结果{i}',index=False)
                frame.to_excel(writer,sheet_name=f'结果{i}',index=False,startrow=3)
    elif ext=='.csv':
        # Tidy long form preserves heterogeneous table schemas in one valid CSV.
        records=[]
        for name,frame in results.items():
            for row in range(len(frame)):
                for col in frame.columns:
                    records.append({'分析':name,'结果行':row+1,'字段':str(col),'值':frame.iloc[row][col]})
        pd.DataFrame(records).to_csv(path,index=False,encoding='utf-8-sig')
    elif ext=='.pdf':
        printer=QPrinter(QPrinter.HighResolution)
        printer.setOutputFormat(QPrinter.PdfFormat)
        printer.setOutputFileName(str(path))
        document=QTextDocument()
        document.setHtml(tables_html(results))
        document.print_(printer)
    else:raise ValueError('请选择 XLSX、CSV 或 PDF 格式')

def main():
    app=QApplication(sys.argv)
    app.setApplicationName('StatMate')
    app.setOrganizationName('StatMate')
    # Qt follows the macOS system appearance and maps Ctrl shortcuts to Command.
    translator=QTranslator(app)
    if translator.load('qtbase_zh_CN', QLibraryInfo.path(QLibraryInfo.TranslationsPath)):
        app.installTranslator(translator)
    window=Window()
    window.show()
    return app.exec()

if __name__=='__main__':
    sys.exit(main())
