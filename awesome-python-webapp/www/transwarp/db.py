#!/usr/bin/env python
# －*－coding:utf-8 -*-

import threading,logging


class Dict(dict):
    '''
    封装dict 可以有a.c的形式 方便ORM模块
    example:
    >>>a = Dict(a=1,b=2,c=3)
    >>>a.c
    3
    >>>a = dict(a=1,b=2,c=3)
    >>>a.c
    error
     
    '''
    def __init__(self, names=(), values=(), **kw):
        super(Dict,self).__init__()
        for k, v in zip(names,values):
            self[k] = v
    
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(r"'Dict' has no attribute %s" % key)
    
    def __setattr__(self, key, value):
        self[key] = value

class DBError(Exception):
    pass

engine = None

#数据库引擎对象
class _Engine(object):
    def __init__(self,connect):
        self._connect = connect
    def connect(self):
        return self._connect()


def create_engine(user, passwd, db, host='127.0.0.1', port=3306 ,**kw):
    import MySQLdb
    global engine 
    if engine is not None:
        raise DBError('Engine is already initialized')
    params = dict(user=user, passwd=passwd, db=db, host=host, port=port)
    engine = _Engine(lambda:MySQLdb.connect(**params)) # **把params当作一个字典传入 why send a func return : 必须的，传递一个object
    logging.info("Init mysql engine <%s> ok" % hex(id(engine)))

#持有数据库连接的上下文对象
class _DbCtx(threading.local):
    def __init__(self):
        self.connection = None
        self.transactions = 0

    def is_init(self):
        return not self.connection is None

    def init(self):
        self.connection = _LasyConnection()
        self.transactions = 0

    def cleanup(self):
        self.connection.cleanup()
        self.connection = None

    def cursor(self):
        return self.connection.cursor()

_db_ctx = _DbCtx()

class _ConnectionCtx(object):
    def __enter__(self):
        global _db_ctx
        self.should_cleanup = False
        if not _db_ctx.is_init():
            _db_ctx.init()
            self.should_cleanup = True
        return self
    
    def __exit__(self, exctype, excvalue, traceback):
        global _db_ctx
        if self.should_cleanup:
            _db_ctx.cleanup()

def with_connection():
    return _ConnectionCtx()

@with_connection
def do_some_db_operation():
    pass

@with_connection
def select(sql, *args):
    pass

@with_connection
def update(sql, *args):
    pass



class _TransactionCtx(object):
    def __enter__(self):
        global _db_ctx
        self.should_close_conn = False
        if not _db_ctx.is_init():
            _db_ctx.init()
            self.should_close_conn = True
        _db_ctx.transactions = _db_ctx.transactions + 1
        return self

    def __exit__(self, exctype, excvalue, traceback):
        global _db_ctx
        _db_ctx.transactions = _db_ctx.transactions - 1
        try:
            if _db_ctx.transactions==0:
                if exctype is None:
                    self.commit()
                else:
                    self.rollback()
        finally:
            if self.should_close_conn:
                _db_ctx.cleanup()

    def commit(self):
        global _db_ctx
        try:
            _db_ctx.connection.commit()
        except:
            _db_ctx.connection.rollback()
            raise

    def rollback(self):
        global _db_ctx
        _db_ctx.connection.rollback()

def with_transaction():
    return _TransactionCtx()

@with_transaction
def do_in_transaction():
    pass

class _LasyConnection(object):  
    def __init__(self):  
        self.connection=None  
  
    def cursor(self):  
        if self.connection is None:  
            connection=engine.connect()  
            #logging.info('open connection <%s>...' % hex(id(connection)))  
            self.connection = connection  
        return self.connection.cursor()  
  
    def commit(self):  
        self.connection.commit()  
  
    def rollback(self):  
        #print '================='  
        #print self.connection  
        self.connection.rollback()  
  
    def cleanup(self):  
        if self.connection:  
            connection = self.connection  
            self.connection=None  
            #logging.info('colse connection <%s>...' %hex(id(connection)))  
            connection.close() 

