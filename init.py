import api.dataManager
import plugins.enabled
database = api.dataManager.databaseObject("./root/blob/xms.db")
dataManager = api.dataManager.dataManager(database, "./root", "./plugins", plugins.enabled)

print(dataManager.executeInitScript())
