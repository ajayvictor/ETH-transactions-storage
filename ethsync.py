from web3 import Web3
import psycopg2
import time
import logging


web3 = Web3(Web3.IPCProvider("/home/geth/.ethereum/geth.ipc"))


logger = logging.getLogger("EthTxs")
logger.setLevel(logging.INFO)
lfh = logging.FileHandler("/var/log/ethtxs.log")
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
lfh.setFormatter(formatter)
logger.addHandler(lfh)

try:
    conn = psycopg2.connect("dbname=<yourDB>")
    conn.autocommit = True
    logger.info("Initial connection to the database")
except:
    logger.info("I am unable to connect to the database (initial)")

cur = conn.cursor()
cur.execute('DELETE FROM public.ethtxs WHERE block = (SELECT Max(block) from public.ethtxs)')
cur.close()
conn.close()

def insertion(blockid, tr):
    time = web3.eth.getBlock(blockid)['timestamp']
    for x in range(0, tr):
        trans = web3.eth.getTransactionByBlock(blockid, x)
        txhash = trans['hash']
        value = trans['value']
        inputinfo = trans['input']
        if (value == 0 and not inputinfo.startswith('0xa9059cbb')):
            continue
        fr = trans['from']
        to = trans['to']
        gasprice = trans['gasPrice']
        gas = web3.eth.getTransactionReceipt(trans['hash'])['gasUsed']
        contract_to = ''
        contract_value = ''
        if inputinfo.startswith('0xa9059cbb'):
            contract_to = inputinfo[10:-64]
            contract_value = inputinfo[74:]
        cur.execute(
            'INSERT INTO public.ethtxs(time, txfrom, txto, value, gas, gasprice, block, txhash, contract_to, contract_value) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)',
            (time, fr, to, value, gas, gasprice, blockid, txhash, contract_to, contract_value))


while True:
    try:
        conn = psycopg2.connect("dbname=<yourDB>")
        conn.autocommit = True
    except:
        logger.info("I am unable to connect to the database")

    cur = conn.cursor()

    cur.execute('SELECT Max(block) from public.ethtxs')
    maxblockindb = cur.fetchone()[0]
    if maxblockindb is None:
        maxblockindb = 46146

    endblock = int(web3.eth.blockNumber)

    logger.info('Max block in db: ' + str(maxblockindb) + '; in chain: ' + str(endblock))

    for block in range(maxblockindb + 1, endblock):
        transactions = web3.eth.getBlockTransactionCount(block)
        if transactions > 0:
            insertion(block, transactions)
        else:
            logger.info('Block ' + str(block) + ' does not contain transactions')
    cur.close()
    conn.close()
    time.sleep(30)