"""双侧检验；逐分析排除缺失值，所有计算由 SciPy/statsmodels 完成。"""
import numpy as np
import pandas as pd
from scipy import stats
import statsmodels.api as sm

METHODS = ['描述性统计', '频数分析', '交叉表与卡方检验', '独立样本 t 检验', '配对样本 t 检验', '单因素方差分析', 'Pearson 相关分析', '线性回归']

def numeric(df, columns):
    for c in columns:
        if not pd.api.types.is_numeric_dtype(df[c]):
            raise ValueError(f'变量“{c}”必须为数值类型，请先在变量视图转换')
        if np.isinf(df[c].dropna().to_numpy(dtype=float)).any():
            raise ValueError(f'变量“{c}”含无穷值')
    return df[columns].dropna()

def analyze(df, method, columns):
    if not columns:
        raise ValueError('请至少选择一个变量')
    if method == METHODS[0]:
        numeric(df, columns)
        rows = []
        for c in columns:
            s = df[c].dropna()
            rows.append([c, len(s), len(df)-len(s), s.mean(), s.std(ddof=1), s.min(), s.median(), s.max()])
        return {'描述性统计':pd.DataFrame(rows, columns=['变量','样本量','缺失数','均值','标准差','最小值','中位数','最大值'])}
    if method == METHODS[1]:
        tables = {}
        for c in columns:
            counts = df[c].value_counts(dropna=True, sort=False)
            tables[f'频数：{c}'] = pd.DataFrame({'取值':counts.index, '频数':counts.values, '有效百分比':counts.values / max(counts.sum(),1)*100})
            tables[f'样本：{c}'] = pd.DataFrame([{'总样本量':len(df),'有效样本量':df[c].count(),'缺失数':df[c].isna().sum()}])
        return tables
    if len(columns) < 2:
        raise ValueError('该分析至少需要两个变量；请按提示顺序选择')
    a,b = columns[:2]
    if method == METHODS[2]:
        d = df[[a,b]].dropna()
        observed = pd.crosstab(d[a], d[b])
        if min(observed.shape) < 2:
            raise ValueError('交叉表的两个变量都至少需要两个类别')
        chi,p,dof,expected = stats.chi2_contingency(observed, correction=False)
        return {'交叉表':observed.reset_index(), 'Pearson 卡方（无连续性校正）':pd.DataFrame([{'样本量':len(d),'卡方':chi,'自由度':dof,'p 值':p,'期望频数小于5的单元格':int((expected<5).sum())}]), '期望频数':pd.DataFrame(expected,index=observed.index,columns=observed.columns).reset_index()}
    if method in (METHODS[3], METHODS[5]):
        numeric(df, [a])
        d = df[[a,b]].dropna()
        groups = [g[a].to_numpy() for _,g in d.groupby(b, observed=True)]
        if len(groups)<2 or any(len(g)<2 for g in groups):
            raise ValueError('至少需要两组，每组至少两个有效观测')
        if method == METHODS[3]:
            if len(groups)!=2:
                raise ValueError('独立样本 t 检验的分组变量必须恰好有两组')
            test = stats.ttest_ind(*groups,equal_var=False)
            result = {'样本量':len(d),'组1样本量':len(groups[0]),'组2样本量':len(groups[1]),'t':test.statistic,'自由度':test.df,'p 值':test.pvalue}
            title = 'Welch 独立样本 t 检验'
        else:
            test = stats.f_oneway(*groups)
            result = {'样本量':len(d),'F':test.statistic,'组间自由度':len(groups)-1,'组内自由度':len(d)-len(groups),'p 值':test.pvalue}
            title = '单因素方差分析（等方差假设）'
        summary = d.groupby(b,observed=True)[a].agg(['count','mean','std']).reset_index().rename(columns={'count':'样本量','mean':'均值','std':'标准差'})
        return {title:pd.DataFrame([result]),'分组描述':summary}
    d = numeric(df, columns)
    if len(d)<3:
        raise ValueError('至少需要三个完整有效观测')
    if any(d[c].nunique()<2 for c in columns):
        raise ValueError('分析变量不能为常数')
    if method == METHODS[4]:
        test = stats.ttest_rel(d[a], d[b])
        return {'配对样本 t 检验':pd.DataFrame([{'样本量':len(d),'平均差':(d[a]-d[b]).mean(),'t':test.statistic,'自由度':test.df,'p 值':test.pvalue}])}
    if method == METHODS[6]:
        rows=[]
        for i,x in enumerate(columns):
            for y in columns[i+1:]:
                r,p=stats.pearsonr(d[x],d[y])
                rows.append([x,y,len(d),r,len(d)-2,p])
        return {'Pearson 相关（整组删除缺失）':pd.DataFrame(rows,columns=['变量1','变量2','样本量','r','自由度','p 值'])}
    if method == METHODS[7]:
        x = sm.add_constant(d[columns[1:]].astype(float))
        if len(d)<=x.shape[1] or np.linalg.matrix_rank(x)<x.shape[1]:
            raise ValueError('观测数不足或自变量完全共线')
        fit=sm.OLS(d[a].astype(float),x).fit()
        ci=fit.conf_int()
        return {'回归模型':pd.DataFrame([{'样本量':int(fit.nobs),'R²':fit.rsquared,'调整 R²':fit.rsquared_adj,'F':fit.fvalue,'模型自由度':fit.df_model,'残差自由度':fit.df_resid,'p 值':fit.f_pvalue}]),'回归系数':pd.DataFrame({'变量':fit.params.index,'B':fit.params.values,'标准误':fit.bse.values,'t':fit.tvalues.values,'自由度':fit.df_resid,'p 值':fit.pvalues.values,'95%下限':ci[0].values,'95%上限':ci[1].values})}
    raise ValueError('未知分析方法')
