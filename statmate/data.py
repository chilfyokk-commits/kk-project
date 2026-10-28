from dataclasses import dataclass, field
from pathlib import Path
import csv
import numpy as np
import pandas as pd
import pyreadstat

@dataclass
class Variable:
    kind: str = '数值'
    label: str = ''
    values: dict = field(default_factory=dict)
    missing: list = field(default_factory=list)
    measure: str = '尺度'

class Dataset:
    def __init__(self, frame=None):
        self.frame = pd.DataFrame() if frame is None else frame.copy()
        self.variables = {str(c): Variable(kind='数值' if pd.api.types.is_numeric_dtype(self.frame[c]) else '文本', measure='尺度' if pd.api.types.is_numeric_dtype(self.frame[c]) else '名义') for c in self.frame}
        self.frame.columns = list(self.variables)

    def clean(self):
        result = self.frame.copy()
        for c, v in self.variables.items():
            result[c] = result[c].replace(v.missing, np.nan)
        return result

    @classmethod
    def load(cls, path):
        ext = Path(path).suffix.lower()
        meta = None
        if ext == '.sav':
            frame, meta = pyreadstat.read_sav(str(path), user_missing=True)
        elif ext in ('.xls', '.xlsx'):
            frame = pd.read_excel(path)
        elif ext in ('.csv', '.txt'):
            encoding = 'utf-8-sig'
            try:
                with open(path, encoding=encoding) as source:
                    sample = source.read(65536)
            except UnicodeDecodeError:
                encoding = 'gb18030'
                with open(path, encoding=encoding) as source:
                    sample = source.read(65536)
            try:
                delimiter = csv.Sniffer().sniff(sample, delimiters=',;\t|').delimiter
            except csv.Error:
                delimiter = ','
            frame = pd.read_csv(path, sep=delimiter, encoding=encoding)
        else:
            raise ValueError('不支持的文件格式')
        obj = cls(frame)
        if meta:
            for c, v in obj.variables.items():
                v.label = meta.column_names_to_labels.get(c) or ''
                v.values = meta.variable_value_labels.get(c, {})
                v.measure = {'nominal': '名义', 'ordinal': '有序', 'scale': '尺度'}.get(meta.variable_measure.get(c), '尺度')
                ranges = meta.missing_ranges.get(c, [])
                for r in ranges:
                    if r['lo'] == r['hi']:
                        v.missing.append(r['lo'])
                    else:
                        # Preserve range semantics by expanding observed missing values.
                        v.missing.extend(frame.loc[frame[c].between(r['lo'], r['hi']), c].dropna().unique().tolist())
        return obj

    def save(self, path):
        ext = Path(path).suffix.lower()
        if ext == '.sav':
            pyreadstat.write_sav(self.frame, str(path), column_labels={c:v.label for c,v in self.variables.items()}, variable_value_labels={c:v.values for c,v in self.variables.items() if v.values}, missing_ranges={c:v.missing for c,v in self.variables.items() if v.missing}, variable_measure={c:{'名义':'nominal','有序':'ordinal','尺度':'scale'}[v.measure] for c,v in self.variables.items()})
        elif ext == '.xlsx':
            self.frame.to_excel(path, index=False)
        elif ext == '.csv':
            self.frame.to_csv(path, index=False, encoding='utf-8-sig')
        else:
            raise ValueError('请选择 CSV、XLSX 或 SAV 格式')
