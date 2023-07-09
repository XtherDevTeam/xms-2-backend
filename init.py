import api.dataManager

database = api.dataManager.databaseObject("./root/blob/xms.db")
dataManager = api.dataManager.dataManager(database, "./root")

print(dataManager.executeInitScript())