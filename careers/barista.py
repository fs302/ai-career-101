
from careers.base_career import BaseCareer

PROFILE = '''
A barista is a skilled coffee professional who expertly brews and serves coffee, 
provides excellent customer service, and possesses extensive knowledge of 
coffee varieties and brewing techniques.
'''

KNOWLEDGE_COFFEE_BEANS = '''
There are several types of coffee beans, with the most common being Arabica and Robusta. Here's more information about these two primary varieties:
	1.	Arabica: Arabica beans are widely regarded as the higher quality and more desirable of the two. They are grown at higher altitudes, typically between 600 to 2000 meters above sea level, in regions with a cool climate. Arabica beans have a more complex and nuanced flavor profile, offering a wide range of notes such as fruit, floral, chocolate, and varying levels of acidity. They generally have a smoother, milder taste with less bitterness.
	2.	Robusta: Robusta beans are hardier and easier to cultivate than Arabica beans. They are grown at lower altitudes, usually below 800 meters, in regions with a warmer climate. Robusta beans have a higher caffeine content and tend to have a stronger, more bitter flavor profile. They often exhibit earthy, nutty, and chocolatey notes. Robusta beans are commonly used in espresso blends and instant coffee due to their ability to provide a rich crema and a robust flavor.
Apart from these main varieties, there are also lesser-known coffee bean types, including:
	3.	Liberica: Liberica beans are less prevalent but have a distinctive flavor. They are known for their larger size, irregular shape, and unique fruity and floral aromatic qualities. Liberica beans are grown in specific regions like the Philippines and have a slightly smoky and bold flavor profile.
	4.	Excelsa: Excelsa beans were previously classified as a type of Liberica but are now considered a separate variety. They offer a unique flavor profile that combines the richness of dark roast with the brightness of light roast. Excelsa beans are known for their tart and fruity notes, as well as their versatility in blending with other coffee beans.
While Arabica and Robusta are the most widely consumed coffee beans, each variety has its own characteristics and taste profiles. Exploring different types of coffee beans can provide coffee lovers with a diverse and enjoyable range of flavors to experience.
'''

KNOWLEDGE_BREWING_TECHNIQUES = '''
Here's a detailed explanation of some popular brewing methods used in coffee preparation:
    1.	Pour-over: Pour-over brewing involves pouring hot water over coffee grounds placed in a filter cone or dripper. The water flows through the coffee bed and extracts the flavors, resulting in a clean and flavorful cup. This method allows for precise control over variables like water temperature, pour rate, and extraction time, which can influence the taste.
	2.	French Press: In a French press, coarsely ground coffee is combined with hot water in a cylindrical glass or metal container. After steeping for a few minutes, a plunger with a mesh filter is pressed down, separating the coffee grounds from the liquid. This method produces a full-bodied and rich cup, as the coffee oils and sediment aren't filtered out.
	3.	Espresso: Espresso is a concentrated form of coffee brewed by forcing hot water under high pressure through finely ground coffee. It's typically brewed using an espresso machine, where water is pumped through the coffee at around 9 bars of pressure. This method quickly extracts intense flavors, resulting in a small serving of strong and flavorful coffee with a crema layer on top.
	4.	AeroPress: The AeroPress is a versatile and compact brewing device. It uses air pressure to extract flavors from coffee grounds. The method involves placing a paper filter inside a plastic chamber, adding coffee and hot water, stirring, and then pressing the plunger, which pushes the coffee through the filter and into a cup. AeroPress allows for various brewing techniques, resulting in a clean and smooth cup of coffee.
	5.	Cold Brew: Cold brew is a method where coffee grounds are steeped in cold or room temperature water for an extended period, usually 12 to 24 hours. The slow extraction process produces a smooth, low-acidity coffee concentrate. The cold brew is typically diluted with water or milk and served over ice for a refreshing and less bitter coffee experience.
'''

class Barista(BaseCareer):
    def __init__(self, name='Barista', profile=PROFILE):
        super().__init__(name, profile)
        self.reset()
    
    def reset(self):
        self.knowledges = {}
        self.memories = []
        self.skills = []
        self.actions = []
        self.add_knowledges("Coffee beans", KNOWLEDGE_COFFEE_BEANS)
        self.add_knowledges("Brewing techniques", KNOWLEDGE_BREWING_TECHNIQUES)
        self.set_skills()
        self.set_actions()
        
    def set_skills(self):
        self.skills.append("coffee making")
        self.skills.append("latte art")
    
    def set_actions(self):
        self.actions.append("make coffee")
        self.actions.append("make latte art")
        self.actions.append("clean espresso machine")
        self.actions.append("clean milk steamer")
        self.actions.append("clean counter")
        self.actions.append("take order")
        self.actions.append("take payment")
        self.actions.append("give change")
        self.actions.append("restock coffee beans")
        self.actions.append("restock milk")
        self.actions.append("restock cups")
        self.actions.append("restock sugar")
        self.actions.append("restock stirrers")
        self.actions.append("restock napkins")
        self.actions.append("restock lids")
        self.actions.append("restock straws")
        self.actions.append("restock cream")