# -*- coding: utf-8 -*-
"""
Created on Mon Jan  6 21:16:58 2020

@author: skjerns
"""
import os, sys
import numpy as np
import logging
from .utils import validkey, strip, lowercase, make_key, valid_filename
from .utils import read_csv, write_csv
from xml.etree import ElementTree as ET
from xml.etree.ElementTree import Element
from copy import deepcopy


class Entry():
    """
    Hello, it's me, Entry
    
    :param test:test
    """
    def __len__(self):
        return len(self._entries)
    
    def __iter__(self):
        return self._entries.__iter__()
    
    def __repr__(self):
        return "<{}({})>".format(self._name, self.attrib)
 
    def __init__(self, attrib=None, parent='.', **kwargs):
        if attrib is None: 
            attrib=dict()
        self.attrib = attrib
        self.__dict__.update(self.attrib)
        self._entries = list()
        self._folder = parent._folder if isinstance(parent, Entry) else parent
        self._parent = parent if isinstance(parent, Entry) else None
        self._name = lowercase(type(self).__name__)
        for key in kwargs:
            self.key = kwargs[key]
        self._autosave()
    
    
    def __setattr__(self, name:str, value:str):
        """
        This will allow to set new attributes with .attrname = value
        while warning the user if builtin methods are overwritten
        """
        methods = dir(type(self))
        super.__setattr__(self, name, value)
        # do not overwrite if it's a builtin method
        if name not in methods and not name.startswith('_') and \
            isinstance(value, (int, float, bool, bytes, str)):
            self.set_attrib(name, value)


    def __getattr__(self, key):
        try:
            i, key = self._get_index(key)
            return self.__dict__[key]
        except:  
            return self.__getattribute__(key)
        raise KeyError(f'{key} not found')


    def __getitem__(self, key):
        if isinstance(key, str):
            i, key = self._get_index(key)
            return self.__dict__[key]
        elif isinstance(key, int):
            return self._entries[key]
        raise KeyError(f'{key} not found')


    def _autosave(self):
        """
        if autosave is enabled, this function will call the autosave
        function of parents until the Unisens object is reached and
        then save when anything is changed.
        """
        try:
            if self._parent is not None:
                self._parent._autosave()
        except:
            pass

    def _check_readonly(self):
        """
        will raise an exception if a write operation 
        is requested to readonly file
        """
        if hasattr(self, '_parent') and self._parent is not None:
            if isinstance(self._parent, str): return True
            self._parent._check_readonly()
        elif hasattr(self, '_readonly'):
            if self._readonly:
                raise IOError(f'Read only, can\'t write to {self._folder}.')
        return True
    

    def _get_index(self, id_or_name, raises=True):
        """
        for a given id or name get the index of the entry in ._entries
        and the key of the entry in __dict__
        """
        id_or_name = make_key(id_or_name)
        
        # we don't care about case, gently ignoring Linux file case-sensitivity
        # first check for exact match
        for i, entry in enumerate(self._entries):
            if hasattr(entry, 'id'):
                id = make_key(entry.id)
                if id.upper()==id_or_name.upper(): return i, id
            else:
                name = entry._name
                if name.upper()==id_or_name.upper(): return i, name
                
        # then check for no file-ext match, eg text matches to text.txt
        found = []
        for i, entry in enumerate(self._entries):
            if hasattr(entry, 'id'):
                id = make_key(entry.id)
                no_ext = id.upper().split('_')[-2:-1][0]
                if no_ext==[]:continue
                if no_ext==id_or_name.upper():
                    found+=[(i, id)]
        if len(found)==1: return found[0]     
        if len(found)>1: KeyError(f'More than one match for {id_or_name}: {found}')
        raise KeyError(f'{id_or_name} not found')
        
    
    def copy(self):
        """
        Create a deep copy of this Entry.
        All references to the parent Unisens object will be removed before.
        
        :returns copy: a Entry object with all attributes as the invoking object
        """
        if hasattr(self, '_parent'):
            _parent = self._parent
            del self._parent
            copy = deepcopy(self)
            self._parent = _parent
        else:
            copy = deepcopy(self)
        return copy
    
    
    def add_entry(self, entry:'Entry', stack=True):
        """
        Add an subentry to this entry
        
        :param entry: A sub entry that should be added, eg CustomAttributes
        :param replace: if the entry is already present it will not be stacked
                        but replaced.
        """
        # there are several Entries that have reserved names.
        # these should not exist double, therefore they are re-set here
        reserved = ['binFileFormat', 'csvFileFormat', 'customFileFormat']
        if entry._name in reserved: 
            stack=False
        
        name = entry.id if hasattr(entry, 'id') else entry._name
        
        if not stack:
            try: self.remove_entry(name)
            except: pass
        
        self._entries.append(entry)
                
        # if an entry already exists with this exact name
        # we put the entry inside of a list and append the new entry
        # with the same name. This way all entries are saved
        name = make_key(name)
        if name in self.__dict__:
            if isinstance(self.__dict__[name], list):
                self.__dict__[name].append(entry)
            else:
                self.__dict__[name] = [self.__dict__[name]]
                self.__dict__[name].append(entry)
        else:
            self.__dict__[name] = entry
        entry._parent = self
        self._autosave()
        return self

    def remove_entry(self, name):
        i, key = self._get_index(name)
        entry = self._entries[i]
        del self._entries[i]
        del self.__dict__[key]
        # if this is an unisens object, also delete the referer there
        if hasattr(self, 'entries'):
            for key, e in self.entries.items():
                if e==entry: del self.entries[key]
        return self


    def set_attrib(self, name:str, value:str):
        """
        Set an attribute of this Entry

        Parameters
        ----------
        name : str
            The name of this attribute
        value : (str, int, float)
            DESCRIPTION.

        Returns
        -------
        self

        """
        name = str(name)
        value = str(value)
        name = validkey(name)
        self.attrib[name] = value
        self.__dict__.update(self.attrib)
        self._autosave()
        return self
    
    def get_attrib(self, name:str, default=None):
        """
        This will allow to set new attributes with .attrname = value
        while warning the user if builtin methods are overwritten
        """
        return self.__dict__.get(name, default)
    
    def remove_attr(self, name:str):
        """
        Removes a custom attribute/value of this entry.
        
        :param key: The name of the custom attribute
        """
        if name in self.attrib: 
            del self.attrib[name]
            del self.__dict__[name]
        else:
            logging.error('{} not in attrib'.format(name))
        self._autosave()
        return self           
        

    def to_element(self):
        element = Element(self._name, attrib=self.attrib.copy())
        element.tail = '\n'
        for subelement in self._entries:
            element.append(subelement.to_element())
        return element
    
    
    def to_xml(self):
        element = self.to_element()
        return ET.tostring(element).decode()
    
    

class FileEntry(Entry):
    """
    This is a Entry subtype that has an ID, ie a file associated with it.
    Subtypes of FileEntry include ValuesEntry, EventEntry, CustomEntry and
    SignalEntry.
    """
    
    def __repr__(self):
        id = self.attrib.get('id', 'None')
        return "<{}({})>".format(self._name, id)
    
    def __init__(self, id, attrib=None, parent='.', **kwargs):
        super().__init__(attrib=attrib, parent=parent, **kwargs)
        if 'id' in self.attrib:
            self._filename = os.path.join(self._folder, self.id)
            if not os.path.exists(self._filename):
                logging.error('File {} does not exist'.format(self.id))     
            self.set_attrib('id', self.attrib['id'])
        elif id:
            if os.path.splitext(str(id))[-1]=='':
                logging.warning('id should be a filename with extension ie. .bin')
            self._filename = os.path.join(self._folder, id)
            self.set_attrib('id', id)
        else:
            raise ValueError('id must be supplied')
        valid_filename(self.id)
        folder = os.path.dirname(self._filename)
        os.makedirs(folder, exist_ok=True)
        if isinstance(parent, Entry): parent.add_entry(self)

        
class SignalEntry(FileEntry):
    
    def __init__(self, id=None,  attrib=None, parent='.', **kwargs):
        super().__init__(id=id, attrib=attrib, parent=parent, **kwargs)
        
        
    def get_data(self, scaled:bool=True, return_type:str='numpy') -> np.array:
        """
        Will try to load the binary data using numpy.
        This might not always work as endianess can't be determined
        with numpy
        
        :param scaled: Scale values using scaling factor or return raw numbers
        :param return_type: numpy, list or pandas. Pandas row indices have the 
                            names of the corresponding channels. List will be
                            in format [[ch_name1, data],[ch_name2, data]]
                            numpy will be as plain numpy array without ch_names
        """
        if return_type!='numpy': raise NotImplementedError
        n_channels = len(self.channel) if isinstance(self.channel, list) else 1
        dtypestr = self.dataType.lower()
        dtype = np.__dict__.get(dtypestr, f'UNKOWN_DATATYPE: {dtypestr}')
        data = np.fromfile(self._filename, dtype=dtype)
        if scaled:
            data = (data * float(self.lsbValue))
        return data.reshape([-1, n_channels]).T
    
    
    def set_data(self, data:np.ndarray, dataType:str=None, ch_names:list=None, 
                       sampleRate:int=256, lsbValue:float=1, unit:str=None, 
                       comment:str=None, contentClass:str=None,
                       adcResolution:int=None, baseline:float=None, **kwargs):
        """
        Set the data that is connected to this SignalEntry.
        The data will in any case be saved with Endianness LITTLE,
        as this is the default for numpy. Data will be saved using
        numpy binary data output.
        
        :param data: an numpy array
        :param dataType: the data type of the data. If None, is array.dtype.
                         Will be used for binary stream output format.
        :param sampleRate: the sample rate of this data
        :param lsbValue: the value with which this data is scaled.
                         this means that       
        :param comment: sets a comment associated with this data
        :param unit: the unit which is indicated, e.g. mV, Ohm, ...
        :param contentClass: sets the content class, e.g. EEG, ECG, ...
        """
        self._check_readonly()

        file = os.path.join(self._folder, self.id)
        
        # if list, convert to numpy array
        if isinstance(data, list):
            # if the list entries are arrays, we can infer the dtype from them
            if isinstance(data[0], np.ndarray) and dataType is None:
                dtype = str(data[0].dtype)
            else:
                dtype = type(data[0][0])
            if dtype==np.int64 or dtype==int: dtype=np.int32
            data = np.array(data, dtype=dtype)
        
        data = np.atleast_2d(data)
        order = sys.byteorder.upper() # endianess
        fileFormat = MiscEntry('binFileFormat', key='endianess', value=order)
        self.add_entry(fileFormat)

        #### dtype inference start
        dtype_mapping = {'float16': 'float',
                         'float32': 'float',
                         'float64': 'double',
                         'int': 'int32'}

        if dataType is None:
            dataType = str(data.dtype).upper()

        dataType = dtype_mapping.get(dataType.lower(), dataType)
        allowed_dtypes = ['DOUBLE', 'FLOAT', 'INT16', 'INT32', 
                          'INT8', 'UINT16', 'UINT32', 'UINT8']
        assert dataType.upper() in allowed_dtypes,\
                f'{dataType} is not in {allowed_dtypes}'

        #### dtype inference end
                
        # if we get a string supplied, we convert to list
        if isinstance(ch_names, str): ch_names = [ch_names]
        
        if ch_names is None and hasattr(self, 'channel') and\
           len(self.channel)==len(data): 
               # this means channel information is present and matches array
               pass
        elif ch_names is not None: 
            # this means new channel names are indicated and will overwrite.
            assert len(ch_names)==len(data), f'len {ch_names}!={len(data)}'
            if hasattr(self, 'channel'):
                logging.warn('Channels present will be overwritten')
                self.remove_entry('channel')
            for name in ch_names:
                channel = MiscEntry('channel', key='name', value=name)
                self.add_entry(channel)
        elif ch_names is None and not hasattr(self, 'channel'):
            # this means no channel names are indicated and none exist
            # we create new generic names for the channels
            logging.info('No channel names indicated, will use generic names')
            for i in range(len(data)):
                channel = MiscEntry('channel', key='name', value=f'ch_{i}')
                self.add_entry(channel)
        else:
            # this means there are channel names there but do not match n_data
            raise ValueError('Must indicate channel names')
        
        # save data using numpy , 
        # .T because unisens reads rows*columns not columns*rows like numpy
        data.T.tofile(file)
        
        if baseline is not None: self.set_attrib('baseline', baseline)
        if sampleRate is not None: self.set_attrib('sampleRate', sampleRate)
        if lsbValue is not None: self.set_attrib('lsbValue', lsbValue)
        if unit is not None: self.set_attrib('unit', unit)
        if comment is not None: self.set_attrib('comment', comment)
        if contentClass is not None: self.set_attrib('contentClass', contentClass)
        if dataType is not None: self.set_attrib('dataType', dataType.lower())
        if adcResolution is not None: self.set_attrib('adcResolution',adcResolution)
        
        # set all other keyword arguments/comments as well.
        for key in kwargs:
            self.set_attrib(key, kwargs[key])
            
        self._autosave()
        return self        

class CsvFileEntry(FileEntry):
    
    def __init__(self, id=None, attrib=None, parent='.', 
                 decimalSeparator='.', separator=';', **kwargs):
        super().__init__(id=id, attrib=attrib, parent=parent, **kwargs)
        assert decimalSeparator and separator, 'Must supply separators'

        if not self.id.endswith('csv'):
            logging.warn(f'id "{id}" does not end in .csv')
        
        csvFileFormat = MiscEntry('csvFileFormat', parent=self)
        csvFileFormat.set_attrib('decimalSeparator', decimalSeparator)
        csvFileFormat.set_attrib('separator', separator)
        self.add_entry(csvFileFormat)
        
            
    
    def set_data(self, data:list, **kwargs):
        """
        Set data to this csv object.
        
        :param data: the data as list or np array
        :param comment: a comment, that will be added to the first line with #
        """
        self._check_readonly()

        assert 'csvFileFormat' in self.__dict__, 'csvFileFormat information'\
                                    'missing: No separator and decimal set'
        assert isinstance(data, (list, np.ndarray)),\
            f'data must be list of lists, is {type(data)}'
        
        sep = self.csvFileFormat.separator
        dec = self.csvFileFormat.decimalSeparator
        
        n_cols = len(data[0])
        if n_cols<2: logging.warn('Should supply at least two columns: '\
                                  'time and data')
        
        write_csv(self._filename, data, sep=sep, decimal_sep=dec)
            
        for key in kwargs:
            self.set_attrib(key, kwargs[key])
        self._autosave()
        return self
        
    def get_data(self, mode:str='list'):
        """
        Will try to load the csv data using a list, pandas or numpy.
        
        :param mode: select the return type
                     valid options: ['list', 'pandas', 'numpy']
        :returns: a list, dataframe or numpy array
        """
        sep = self.csvFileFormat.separator
        dec = self.csvFileFormat.decimalSeparator
        
        if mode in ('numpy', 'np', 'array'):
            lines = np.genfromtxt(self._filename, delimiter=sep, 
                                 dtype=str)
        elif mode in ('pandas', 'pd', 'dataframe'):
            import pandas as pd
            lines = pd.read_csv(self._filename, sep=sep,
                               header=None, index_col=None)
        elif mode == 'list':
            lines = read_csv(self._filename, sep=sep, decimal_sep=dec,
                             convert_nums=True)
        else:
            raise ValueError('Invalid mode: {}, select from'
                             '["numpy", "pandas", "list"]'.format(mode))
        return lines


class ValuesEntry(CsvFileEntry):
    """
    Hello, it's me, ValuesEntry
    
    :param test: test
    """
    
    def __init__(self, id=None, attrib=None, parent='.' , **kwargs):
        super().__init__(id=id, attrib=attrib, parent=parent, **kwargs)
        
    def set_data(self, data:list, ch_names=None, **kwargs):
        # if we get a string supplied, we convert to list
        super().set_data(data, **kwargs) 
        
        if isinstance(ch_names, str): ch_names = [ch_names]
        n_cols = len(data[0])-1

        if ch_names is None and hasattr(self, 'channel') and\
           len(self.channel)==n_cols: 
               # this means channel information is present and matches array
               pass
        elif ch_names is not None: 
            # this means new channel names are indicated and will overwrite.
            assert len(ch_names)==n_cols, f'len {ch_names}!={len(data)}'
            if hasattr(self, 'channel'):
                logging.warn('Channels present will be overwritten')
                self.remove_entry('channel')
            for name in ch_names:
                channel = MiscEntry('channel', key='name', value=name)
                self.add_entry(channel)
        elif ch_names is None and not hasattr(self, 'channel'):
            # this means no channel names are indicated and none exist
            # we create new generic names for the channels
            logging.info('No channel names indicated, will use generic names')
            for i in range(n_cols):
                channel = MiscEntry('channel', key='name', value=f'ch_{i}')
                self.add_entry(channel)
        else:
            # this means there are channel names there but do not match n_data
            raise ValueError('Must indicate channel names')
        self._autosave()
        return self

    
class EventEntry(CsvFileEntry):
    def __init__(self, id=None, attrib=None, parent='.' , **kwargs):
        super().__init__(id=id, attrib=attrib, parent=parent, **kwargs)
        
    
class CustomEntry(FileEntry):
    
    def __init__(self, id=None, **kwargs):
        super().__init__(id=id, **kwargs)  
        self._autosave()
        
    def get_data(self, dtype='auto'):
        """
        Will load the binary data of this CustomEntry.
        
        The following datatypes can be loaded automatically:
            text:  .txt .csv .ini
            image: .jpeg .jpg .bmp .png .tif .gif
            json:  .json (using json-tricks or json)
            numpy: .npy
            binary: anything else
        
        :param dtype: [binary, image, text, numpy, json]
        :returns: the binary data or the otherwise loaded data
        """
        try:
            import json_tricks as json
        except:
            import json
            logging.warn('json_tricks not installed, can\'t load numpy array '\
                         'automatically. install with pip install json-tricks')

        if dtype=='auto':
            ext = os.path.splitext(self._filename)[-1].lower()
            txt_exts = ['.txt', '.csv', '.ini']
            img_exts = ['.jpeg', '.jpg', '.bmp', '.png', '.tif', '.gif']
            
            if ext in img_exts:
                dtype='image'
            elif ext in txt_exts:
                dtype='text'
            elif ext=='.json':
                dtype='json'
            elif ext=='.npy':
                dtype='numpy'
            else:
                dtype='binary'
                
        if dtype=='binary':
            with open(self._filename, 'rb') as f:
                data = f.read()
        elif dtype=='text':
            with open(self._filename, 'r') as f:
                data = f.read()
        elif dtype=='image':
            try: 
                import imageio
                data = imageio.imread(self._filename)
            except: 
                logging.error('can\'t load: imageio not installed. \n'\
                                  'run pip install imageio')
                with open(self._filename, 'rb') as f:
                    data = f.read()
            
        elif dtype=='json':
            with open(self._filename, 'r') as f:
                data = json.load(f)
        elif dtype=='numpy':
            data = np.load(self._filename)
        else:
            raise ValueError('unknown dtype {}'.format(dtype))
            
        return data
    
    
    def set_data(self, data, dtype='auto', **kwargs):
        """
        Will save custom data to disk.
        
        :param data: the data to be saved to disc.
        :param dtype: binary or image.
        :returns: the binary data or an PIL.Image
        """
        self._check_readonly()
        try:
            import json_tricks as json
            tricks_installed = True
        except:
            import json
            tricks_installed = False
            logging.warn('json_tricks not installed, can\'t save numpy array'\
                         'automatically. install with pip install json-tricks')
        
        # infer datatype automatically
        if dtype=='auto':
            ext = os.path.splitext(self._filename)[-1].lower()
            txt_exts = ['.txt', '.csv', '.ini']
            img_exts = ['.jpeg', '.jpg', '.bmp', '.png', '.tif', '.gif']
            
            if ext in img_exts:
                dtype='image'
            elif ext in txt_exts:
                dtype='text'
            elif ext=='.json':
                dtype='json'
            elif ext=='.npy':
                dtype='numpy'
            else:
                dtype='binary'
          
        # file saving from here on
        if dtype=='binary':
            with open(self._filename, 'wb') as f:
                f.write(data)
        elif dtype=='text':
            with open(self._filename, 'w') as f:
                f.write(data)
        elif dtype=='image':
            try: import imageio
            except: logging.error('can\'t save: imageio not installed. \n'\
                                  'run pip install imageio')
            imageio.imsave(self._filename, data)
        elif dtype=='json':
            with open(self._filename, 'w') as f:
                if tricks_installed:
                    json.dump(data, f, allow_nan=True)
                else:
                    json.dump(data, f)
        elif dtype=='numpy':
            data = np.save(self._filename, data)
        else:
            raise ValueError('unknown dtype {}'.format(dtype))
            
        for key in kwargs:
            self.set_attrib(key, kwargs[key])
        self._autosave()
        return self
    
    
class CustomAttributes(Entry):
    def __init__(self, key:str=None, value:str=None, **kwargs):
        super().__init__(**kwargs)   
        if key and value:
            self.set_attrib(key, value)
        
    def to_element(self):
        element = Element(self._name, attrib={})
        element.tail = '\n  \n  \n  '
        element.text = '\n'
        for key in self.attrib:
            customAttribute = MiscEntry(name = 'customAttribute')
            customAttribute.key = key
            customAttribute.value = self.attrib[key]
            subelement = customAttribute.to_element()
            element.append(subelement)
        return element
    
    def add_entry(self, entry:'MiscEntry'):
        if entry._name != 'customAttribute':
            logging.error('Can only add customAttribute type')
            return
        self.set_attrib(entry.key, entry.value)
        self._autosave()
        
  
class MiscEntry(Entry):
    def __init__(self, name:str, key:str=None, value:str=None, **kwargs):
        super().__init__(**kwargs) 
        self._name = strip(name)
        if key and value:
            self.set_attrib(key, value)
        self._autosave()
        
        
class CustomAttribute(MiscEntry):
    def __new__(*args,**kwargs):
        return MiscEntry('customAttribute', **kwargs)



        
        
        
        
        