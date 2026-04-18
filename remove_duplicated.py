import api.dataManager
import plugins.enabled
database = api.dataManager.databaseObject("./root/blob/xms.db")
dataManager = api.dataManager.dataManager(database, "./root", "./plugins", plugins.enabled)


counted = []
counts = dataManager.db.query('select * from playCount order by path desc')
for i in counts:
    if (i['path'], i['owner']) in counted:
        print(f'Record #{i["id"]}: duplicated, deleting')
        dataManager.db.query('delete from playCount where id = ?', (i['id'], ))
    else:
        counted.append((i['path'], i['owner']))
        
counts = dataManager.db.query('select * from playCount order by path desc')
print('Final result:')
print('id|path|owner|plays')
for i in counts:
    print(f'{i["id"]}|{i["path"]}|{i["owner"]}|{i["plays"]}')
    
i = ''
while i != 'y' and i != 'n':
    i = input('Commit changes?(y/n)')
    
if i == 'y':
    dataManager.db.db.commit()
    print('Commited changes.')
else:
    print('Discarded changes.')
    