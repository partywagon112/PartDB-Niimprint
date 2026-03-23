import requests

class PartDB:
    ELEMENT_TYPES = ["part"] 

    def __init__(self, url: str, token: str):
        self.url = url
        self.header = {
            'Authorization': f"Bearer {token}",
            'accept': 'application/json',
            'Content-Type': 'application/json'
        }
    
    def __get(self, endpoint, *args, **kwargs):
        return requests.get(self.url+endpoint, headers=self.header, *args, **kwargs)
    
    def __post(self, endpoint, *args, **kwargs):
        return requests.post(self.url+endpoint, headers=self.header, *args, **kwargs)

    def postLabelGenerationRequest(self, profileId: int, elementIds: list[str], elementType: str = "part") -> bytes:
        if self.getLabelProfile(profileId) == 404:
            return None
        
        if elementType not in PartDB.ELEMENT_TYPES:
            return None
        
        if elementType == "part":
            for id in elementIds:
                if self.getPart(id) == 404:
                    return None

        data = {
            "profileId":int(profileId),
            "elementIds": ",".join(list(map(str, elementIds))),
            "elementType":str(elementType)
        }

        response = self.__post(f"/api/labels/generate", json=data)

        if response.status_code != 200:
            return response.status_code
        
        return response.content


    def getInfo(self) -> dict:
        response = self.__get(f"/api/info")
        if response.status_code != 200:
            return response.status_code
        
        return response.json()

    def getAttachments(self) -> dict:
        response = self.__get(f"/api/attachments")
        if response.status_code != 200:
            return response.status_code
        
        return response.json()
    
    def getAttachment(self, id) -> dict:
        response = self.__get(f"/api/attachments/{id}")
        if response.status_code != 200:
            return response.status_code
        
        return response.json()

    def getAttachmentTypes(self) -> dict:
        response = self.__get(f"/api/attachments_types")
        if response.status_code != 200:
            return response.status_code
        
        return response.json()
    
    def getAttachmentType(self, id) -> dict:
        response = self.__get(f"/api/attachments_types/{id}")
        if response.status_code != 200:
            return response.status_code
        
        return response.json()

    def getLabelProfile(self, id: int) -> dict:
        response = self.__get(f"/api/label_profiles/{id}")
        if response != 200:
            return response.status_code
        
        return response.json()

    def getLabelProfiles(self) -> list:
        response = self.__get(f"/api/label_profiles")

        if response.status_code != 200:
            return response.status_code
        
        return response.content
    
    def getParameter(self, id) -> dict:
        response = self.__get(f"/api/parameters/{id}")

        if response.status_code != 200:
            return response.status_code
        
        return response.content

    def getCategories(self) -> list:
        response = self.__get(f"/api/categories")
        if response.status_code != 200:
            return response.status_code
        
        return response.json()
    
    def getCategory(self, id) -> dict:
        response = self.__get(f"/api/categories/{id}")
        if response.status_code != 200:
            return response.status_code
        
        return response.json()
    
    def getCategoryChildren(self, id) -> dict:
        response = self.__get(f"/api/categories/{id}/children")
        if response.status_code != 200:
            return response.status_code
        
        return response.json()

    def getParts(self) -> list:
        response = self.__get(f"/api/parts")
        if response.status_code != 200:
            return response.status_code
        
        return response.json()
    
    def getPart(self, id) -> dict:
        response = self.__get(f"/api/parts/{id}")
        if response.status_code != 200:
            return response.status_code

        return response.json()

    def getPartsLots(self) -> list:
        response = self.__get(f"/api/parts_lots")
        if response.status_code != 200:
            return response.status_code
        
        return response.json()
    
    def getPartsLot(self, id) -> dict:
        response = self.__get(f"/api/parts_lots/{id}")
        if response.status_code != 200:
            return response.status_code
        
        return response.json()
    
    def getStorageLocations(self) -> list:
        response = self.__get(f"/api/storage_locations")
        if response.status_code != 200:
            return response.status_code
        
        return response.json()
    
    def getStorageLocation(self, id) -> dict:
        response = self.__get(f"/api/storage_locations/{id}")
        if response.status_code != 200:
            return response.status_code
        
        return response.json()
    
    def getSuppliers(self) -> list:
        response = self.__get(f"/api/suppliers")
        if response.status_code != 200:
            return response.status_code
        
        return response.json()

    def getSupplier(self, id) -> dict:
        response = self.__get(f"/api/suppliers/{id}")
        if response.status_code != 200:
            return response.status_code
        
        return response.json()

    def getCurrencys(self) -> dict:
        response = self.__get(f"/api/currencies")
        if response.status_code != 200:
            return response.status_code
        
        return response.json()

    def getCurrency(self, id) -> dict:
        response = self.__get(f"/api/currencies/{id}")
        if response.status_code != 200:
            return response.status_code
        
        return response.json()

    def getPriceDetails(self) -> dict:
        response = self.__get(f"/api/pricedetails")
        if response.status_code != 200:
            return response.status_code

        return response.json()

    def getPriceDetail(self, id) -> dict:
        response = self.__get(f"/api/pricedetails/{id}")
        if response.status_code != 200:
            return response.status_code

        return response.json()
    
    def getProjects(self) -> dict:
        response = self.__get(f"/api/projects")
        if response.status_code != 200:
            return response.status_code

        return response.json()

    def getProject(self, id) -> dict:
        response = self.__get(f"/api/projects/{id}")
        if response.status_code != 200:
            return response.status_code

        return response.json()
    
    def getProjectBOMEntries(self) -> dict:
        response = self.__get(f"/api/project_bom_entries")
        if response.status_code != 200:
            return response.status_code

        return response.json()

    def getProjectBOMEntry(self, id) -> dict:
        response = self.__get(f"/api/project_bom_entries/{id}")
        if response.status_code != 200:
            return response.status_code

        return response.json()
    
    def getApiToken(self):
        response = self.__get(f"/api/tokens/current")
        if response.status_code != 200:
            return response.status_code

        return response.json()
