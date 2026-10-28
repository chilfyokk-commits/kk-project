import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import numpy as np
import pandas as pd
import pytest
from scipy import stats
from statmate.data import Dataset
from statmate.analysis import analyze, METHODS

@pytest.fixture(scope='session')
def app():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])

def first(method,df,cols):
    return next(iter(analyze(df,METHODS[method],cols).values())).iloc[0]

def test_description_and_missing():
    ds=Dataset(pd.DataFrame({'x':[1.,2.,3.,99.,np.nan]}))
    ds.variables['x'].missing=[99]
    row=first(0,ds.clean(),['x'])
    assert row['样本量']==3
    assert row['缺失数']==2
    assert row['均值']==2
    assert row['标准差']==1

def test_welch():
    a=np.array([2.,4.,5.,7.,8.]); b=np.array([5.,6.,9.,11.])
    df=pd.DataFrame({'x':list(a)+list(b),'g':['a']*5+['b']*4})
    r=first(3,df,['x','g'])
    # Independent calculation of Welch statistic and Satterthwaite df.
    va=a.var(ddof=1)/len(a); vb=b.var(ddof=1)/len(b)
    t=(a.mean()-b.mean())/np.sqrt(va+vb)
    dof=(va+vb)**2/(va**2/(len(a)-1)+vb**2/(len(b)-1))
    assert r['t']==pytest.approx(t)
    assert r['自由度']==pytest.approx(dof)
    assert r['p 值']==pytest.approx(2*stats.t.sf(abs(t),dof))

def test_paired_and_correlation():
    df=pd.DataFrame({'a':[1.,2.,3.,4.,5.],'b':[2.,4.,4.,5.,8.]})
    delta=df.a-df.b
    r=first(4,df,['a','b'])
    assert r['t']==pytest.approx(delta.mean()/(delta.std(ddof=1)/np.sqrt(5)))
    assert r['自由度']==4
    r=first(6,df,['a','b'])
    assert r['r']==pytest.approx(np.corrcoef(df.a,df.b)[0,1])

def test_chi_square_and_anova():
    df=pd.DataFrame({'a':['x']*30+['y']*30,'b':['m']*10+['n']*20+['m']*20+['n']*10})
    tables=analyze(df,METHODS[2],['a','b'])
    r=list(tables.values())[1].iloc[0]
    assert r['卡方']==pytest.approx(20/3)
    assert r['自由度']==1
    d=pd.DataFrame({'x':[1.,2.,3.,4.,5.,6.,7.,8.,9.],'g':['a']*3+['b']*3+['c']*3})
    r=first(5,d,['x','g'])
    assert r['F']==pytest.approx(27)
    assert r['组间自由度']==2
    assert r['组内自由度']==6

def test_regression():
    x=np.arange(1.,8.)
    y=3+2*x+np.array([1.,-1.,0.,0.,0.,-1.,1.])
    tables=analyze(pd.DataFrame({'y':y,'x':x}),METHODS[7],['y','x'])
    coef=tables['回归系数']
    assert coef.B.tolist()==pytest.approx([3.,2.])
    assert tables['回归模型'].iloc[0]['残差自由度']==5
    assert np.isfinite(coef['p 值']).all()

def test_frequency_and_validation():
    df=pd.DataFrame({'x':[1.,1.,2.,np.nan]})
    tables=analyze(df,METHODS[1],['x'])
    assert tables['频数：x']['频数'].tolist()==[2,1]
    assert tables['频数：x']['有效百分比'].sum()==pytest.approx(100)
    with pytest.raises(ValueError):analyze(pd.DataFrame({'a':['x'],'b':[1]}),METHODS[0],['a'])
    with pytest.raises(ValueError):analyze(pd.DataFrame({'a':[1,1,1],'b':[2,3,4]}),METHODS[6],['a','b'])

@pytest.mark.parametrize('ext',['csv','xlsx','sav','txt'])
def test_import_export(tmp_path,ext):
    ds=Dataset(pd.DataFrame({'score':[1.,2.,99.],'group':[1.,2.,1.]}))
    ds.variables['group'].label='性别'
    ds.variables['group'].values={1.:'男',2.:'女'}
    ds.variables['group'].measure='名义'
    ds.variables['score'].missing=[99.]
    path=tmp_path/f'data.{ext}'
    if ext=='txt':ds.frame.to_csv(path,sep='\t',index=False)
    else:ds.save(path)
    restored=Dataset.load(path)
    pd.testing.assert_frame_equal(ds.frame,restored.frame,check_dtype=False)
    if ext=='sav':
        assert restored.variables['group'].label=='性别'
        assert restored.variables['group'].values=={1.:'男',2.:'女'}
        assert restored.clean().score.isna().sum()==1

def test_gui_and_exports(app,tmp_path):
    from statmate.app import Window, export_results
    from PySide6.QtCore import Qt
    window=Window()
    window.dataset=Dataset(pd.DataFrame({'x':[1.,2.,3.]}))
    window.refresh()
    assert window.model.setData(window.model.index(0,0),'4',Qt.EditRole)
    assert window.dataset.frame.iloc[0,0]==4
    assert not window.model.setData(window.model.index(0,0),'错误',Qt.EditRole)
    results=analyze(window.dataset.clean(),METHODS[0],['x'])
    for ext in ['xlsx','csv','pdf']:
        path=tmp_path/f'result.{ext}'
        export_results(results,path)
        assert path.stat().st_size>100
        if ext=='pdf':assert path.read_bytes().startswith(b'%PDF')
    window.dirty=False
    window.close()

@pytest.mark.parametrize('content,encoding,columns',[
    ('score\n1\n2\n3\n','utf-8',['score']),
    ('分数;组别\n1;甲\n2;乙\n','gb18030',['分数','组别']),
    ('a,b\n"hello, world",2\n','utf-8',['a','b']),
])
def test_text_edge_cases(tmp_path,content,encoding,columns):
    path=tmp_path/'sample.csv'
    path.write_text(content,encoding=encoding)
    ds=Dataset.load(path)
    assert ds.frame.columns.tolist()==columns
    assert len(ds.frame)>0

def test_event_loop_and_variable_edit(app):
    from statmate.app import Window
    window=Window()
    window.dataset=Dataset(pd.DataFrame({'x':[1.,2.,3.]}))
    window.refresh()
    window.show()
    app.processEvents()
    window.variable_view.item(0,2).setText('课程成绩')
    assert window.dataset.variables['x'].label=='课程成绩'
    window.variable_view.item(0,4).setText('[99]')
    assert window.dataset.variables['x'].missing==[99.]
    window.add_row()
    assert len(window.dataset.frame)==4
    window.dirty=False
    window.close()
