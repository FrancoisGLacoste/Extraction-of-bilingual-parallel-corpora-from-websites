#-*- encoding: utf-8 -*-
" mecCorporaExtraction.py"

from __future__ import unicode_literals, division #, print_function  # à activer si en python2.7   
import requests  
import json
import os
from bs4 import BeautifulSoup
import time # for precise timing with clock() method

global lastRequestTime    # is it needed to declare it here ??? 

        
def openWebPage(url , delay):
    global lastRequestTime
    
    #  initialisation 
    r = None
    soup = None 
    
    currentTime = time.clock()   # in second      
    timeDiff = currentTime - lastRequestTime
    print 'Time from the last request to the mec wesite:  %f'%timeDiff
    if timeDiff < delay:
        newDelay = delay - timeDiff
        print 'Sorry, we still have to wait  %1.3f sec to comply with the "robots.txt" file.  ' % newDelay
        time.sleep(newDelay)
    
    try:        
        # HTTP request   :  would it be more polite to be more properly identified in the request ?
        r = requests.get( url, verify=False ) # dont have to check for SSL ; 
    except :  pass
    #  requests exceptions:  http://docs.python-requests.org/en/master/_modules/requests/exceptions/
        
    if r is None :
        print "The HTTP request fails for the following url: \n%s \n "  %url
    else: 
        lastRequestTime =currentTime
    
        #  opening in soup  
        soup = BeautifulSoup(r.text, "lxml")
        if soup is None: 
            print "No proper beautiful soup response for the following url: \n%s \n "  %url 
        else: 
            print "We got a beautiful soup response for the following url: \n%s \n " %url 
        
    return r, soup
        

def extractCategories(soup):
    """  for either Fr or Eng version,   extract links and category names """
    
    catNames =list() #  ordered list of category names (a bijection  Eng <--> Fr)
    catLinkList =list()
    catLinkDict =dict() #  of the form :  {categoryNames[0]:  corresponding link, .... }
    
    for n in soup.findAll('div', {"class": "yCmsComponent flexigrid__tile"} ):
      
        newLink = n.find('a',{"class":"subcategory-nav__header js-promo-click-track-link"}).get('href')  
        newName= n.find('h3',{"class":"subcategory-nav__header subcategory-nav__header-link js-promo-click-track-link"} ).get_text()
        
        # links that end with a word included in the "exclusionList" is not related to a proper category:
        exclusionList = ["onclearance", "new"] 
        exclusionTest = [ newLink[-len( word ):] != word for word in exclusionList ]
        if all(exclusionTest):
            catNames.append(newName)        
            catLinkList.append(newLink)
            catLinkDict[newName]=newLink
        
            ### test
            print '%s'%catNames[-1] 
            print '%s\n'%catLinkDict[  catNames[-1] ]
        
    return catNames,catLinkDict

def extractItemList(soup):

    """  for either Fr or Eng version,  for a given category, extract and return the item list, their url and the category nextPage (if existant)"""
    itemNameList =list()
    itemUrlList =list()
    nextPage = None   
     
    productList = soup.findAll('a', {'class':"product__name__link js-grid-url js-product-click-track-link js-product-view-track"})   
    for product in productList:
        itemUrl = product.get('href')
        itemLongName = product.get_text()
        itemNameList.append(itemLongName)
        itemUrlList.append(itemUrl)
    
    ###  extraction ot the next page link, if it exists: 
    nextPage_a = soup.find('a', {"class":"pagination__link pagination__link--next js-product-tile-takeover__next-page"})
    if nextPage_a is not None:         
         # get(['href'])  returns something like "981?page=11"; we rather want nextPage of the form "?page=11".
        nextPage = '?' + nextPage_a.get('href').split('?')[1]

    return itemNameList, itemUrlList, nextPage
    

def saveResults(filename,result):
    '''' SAVE the result '''

    with open(filename, 'wb')  as f:   # erasing any eventual content of the file
        json.dump(result, f) 
        done = True
        print 'saved... \n'
    return done    


def openResults(filename):
    
    os.getcwd()
    with open(filename, 'rb') as f: 
        result = json.load(f)
        print '%s open\n'%filename
    return result 

def extractItem(soup):
    itemDict =dict()  #  {'classification':  [vetements, "Chemises et hauts","Hauts sans manches "], 'description':[parag1, parag2, ...] }  
    #given the detailed webpage of an item, open and scrape it. 

    # classification: tags used in the classification in the same "upper bar"
    #longName : name used in the title  in bold character  ( ex:  Camisole Elyse pour MEC - Femmes) 
    # shortName : the name used in the "upper bar"; ( ex:  Camisole Elyse ) 
    # description: a list of strings ; one string by paragraph or by bullet point
    
    ### fullName extraction 
    '''example:  <h1 class="product__name">Smartwool Isto Retro Beanie - Unisex</h1>   '''
    fullName = soup.find('h1').get_text()
    
    ### classification and shortName extraction 
    '''ex:  <li class="breadcrumbs__item"><a class="breadcrumbs__text" href="/en/products/clothing/c/981">Clothing</a></li>
            <li class="breadcrumbs__item"><a class="breadcrumbs__text" href="/en/products/clothing/clothing-accessories/c/982">Clothing accessories</a></li>
            <li class="breadcrumbs__item"><a class="breadcrumbs__text" href="/en/products/clothing/clothing-accessories/headwear/c/993">Hats and toques</a></li>
            <li class="breadcrumbs__item"><a class="breadcrumbs__text" href="/en/products/clothing/clothing-accessories/headwear/toques/c/1000">Toques</a></li>
            <li class="breadcrumbs__item"><span class="breadcrumbs__text"> pom pom hat</span></li>         '''
    breadcrumbs = soup.findAll('li', {'class':"breadcrumbs__item"})
    categoryAgain = breadcrumbs[2].find('a').get_text()                     #  should be same as itemCategory: in the example : 'Clothing'
    shortName = breadcrumbs[-1].find('span').get_text()                     # in the example: 'pom pom hat'
    classification = [b.find('a').get_text() for b in breadcrumbs[3:-1] ]   # in the example:  ['Clothing accessories', 'Hats and toques', 'Toques']
    
    ### extraction of description 
    '''  ex: <div id="pdp-description" class="accordion__branch__control js-accordion-branch-control" aria-hidden="false">
             <p>As though your gran knitted it on #6 needles, this beanie is made from thick "novelty" yarn for a perfectly imperfect homespun look.</p><ul> 
             <li>Made of merino and acrylic, in a heavy, double knit style.</li>
             <li>Optimally sized pom pom.</li></ul></div>    </div>             '''
    descript = soup.find('div', {"id":"pdp-description"})
    descript_p =  [ p.get_text()  for p  in descript.findAll('p') ]              #  list of paragraphs (in string) 
    descript_li = [ li.get_text() for li in descript.findAll('li')]         #  python list of a "list" of bullet points  (in string
    
    
    itemDict['classification'] = classification                             #  a list of string  
    itemDict['shortName']      = shortName                                  #  a string
    itemDict['fullName']       = fullName                                   #  a string
    itemDict['description']    = descript_p + descript_li                   # a list of string
    return itemDict


def extractCategoryLoop(website, delay):
    ''' loop over extractCategory()  '''
    categoryNames = {'Eng': list(), 'Fr':list()} # ordered list of category names (a bijection  Eng <--> Fr)
    categoryLinks = {'Eng': dict(), 'Fr':dict()} #   dictionaries are:  {categoryNames[0]:  corresponding link, .... }
    soupBug = list()
    
    for lang in ['Fr','Eng']:
        ###  for each language, open website main page and extract categories names and categories links
        r,soup = openWebPage(website[lang ], delay)
        if soup is None: 
            soupBug.append( website[lang ] )
            categoryLinks[lang] = None
            categoryNames[lang] = None
            continue  
        catNames,catLinkDict= extractCategories(soup)
        categoryLinks[lang] = catLinkDict  
        categoryNames[lang] = catNames
    return categoryNames, categoryLinks, soupBug


def extractItemListLoop(lang, catName, website, delay, filename, result):
    '''  loop over extractItemList() 
    result =[categoryNames, categoryLinks, itemNames, itemLinks, items, soupBug]'''
    categoryNames = result[0]
    categoryLinks = result[1]
    itemNames     = result[2]  
    itemLinks     = result[3]
    items         = result[4]
    soupBug       =result[-1]
    
    ### open the nextPage of a category and return the item list.
    link = website[lang ] + categoryLinks[lang][catName]
    
    # cannot know the number of pages in a given category before scraping them. 
    nextPage ='0'                                # meaning next page of page=0 exists 
    itemLinks_thisCat=list()                     # list of all item links for this category
    itemNames_thisCat=list()                     # list of all item names for this category
    while nextPage:                              # continue if nextPage not None, exit if nextPage is None 
        newLink = link
        if nextPage !='0':  newLink += nextPage  
        r, soup = openWebPage(  newLink, delay)   
        if soup is None: 
            soupBug.append( newLink )
            itemNameList = None
            itemLinkList= None
            break            # we want to get out from the while loop       
        
        print '%s; '%nextPage       # i.e. the page to be scraped now
        # nextPage: a string of the form "?page=4";  or is None when no additional page exists
        itemNameList, itemLinkList, nextPage= extractItemList(soup) 
        itemLinks_thisCat.extend(itemLinkList)
        itemNames_thisCat.extend(itemNameList)
    
    ### itemNames, itemLinks: dictionaries of dictionaries of lists:
    itemNames[lang][ catName ] = itemNames_thisCat
    itemLinks[lang][ catName ] = itemLinks_thisCat
        
    ### SAVE the results 
    result1 = [categoryNames, categoryLinks, itemNames, itemLinks, items, soupBug]
    saveResults(filename, result1)                     
    # itemNames is finally not useful since we find it again it the page, but we still return it just in case... 
    
    return result1


def extractItemLoop(lang, catName,  website, delay, filename, result):
    '''loop over extractItem() :  for the regarded category and language, for each item in the list, open the item webpage and extract its details
    result=[categoryNames, categoryLinks, itemNames, itemLinks, items, soupBug]
    '''
    categoryNames = result[0]
    categoryLinks = result[1]
    itemNames     = result[2]  
    itemLinks     = result[3]
    items         = result[4]
    soupBug       = result[-1]
    
    print '\n%s, %s\n: '% (catName, lang)
    itemList =list()                       # the list of items for one category and one language
    for lk in itemLinks[lang][ catName ]:
        itemDict = dict()
        link = website[lang ] + lk
        r, soup = openWebPage(  link, delay)   
        if soup is None: 
            soupBug.append( link )
            items[lang][catName]= None
            break                           # we want to get out from the "for" loop                           
        
        itemDict = extractItem(soup)        #  the dictionary that describes an item
        itemList.append(itemDict)
        items[lang][catName]=itemList       #  a lang-dict of category-dict of a list of item dictionaries of lists and strings
        
        ### SAVE the results  
        result1 = [categoryNames, categoryLinks, itemNames, itemLinks, items, soupBug]
        saveResults(filename, result1)                     
    return result1



def main():
    
    ###  initialisation :
    global lastRequestTime 
    lastRequestTime = -5      # in seconds
    delay =5.1 # robots.txt requires delay >= 5  seconds
    
    filename = 'MECscrapping_july2018.json'
    siteEng = 'http://www.mec.ca/en/'
    siteFr  = 'http://www.mec.ca/fr/'
    website ={'Eng':siteEng, 'Fr':siteFr}
    soupBug = list()                                  #  a list of url that fail to open. 
    categoryNames = {'Eng': list(), 'Fr': list()}     #  contains lists of category names (bijection Eng <--->  Fr ) 
    categoryLinks = {'Eng': dict(), 'Fr': dict()}     #  dictionaries are:  {categoryNames[0]:  corresponding link, .... }
    itemNames     = {'Eng': dict(), 'Fr': dict()}     #  A language-dict of category-dict that contains the lists of item names ( bijection  Eng <--> Fr, for corresponding category)
    itemLinks     = {'Eng': dict(), 'Fr': dict()}     #  same  as itemNames  but with links   
    items         = {'Eng': dict(), 'Fr': dict()}     #  A language-dict of category-dict of item-dictionaries that contains some description and details of the item. 
    
    categoryNames, categoryLinks, soupBug = extractCategoryLoop(website, delay)
        
    ### Save the temporary results 
    result = [categoryNames, categoryLinks, itemNames, itemLinks, items, soupBug]
    saveResults(filename,result)     

    for lang in ['Fr','Eng']:        
        print '\n%s\n'%lang
        for catName in categoryNames[lang]:
            print '\n%s:  '%catName            
            ### given a category and a language, extract a list of all item links and names from category pages
            ### fill itemNames[lang][catName], itemLinks[lang][catName], 
            ### update and save result in filename.json
            result1 = extractItemListLoop(lang,catName, website, delay, filename, result)

            ### given a category and a language, for each item in the list, open the item webpage and extract its details 
            ###  fill items[lang][catName]  , update and save result = [categoryNames, categoryLinks, itemNames, itemLinks, items, soupBug] in filename.json
            result = extractItemLoop(lang, catName,  website, delay, filename, result1)
            

def restart():
    ''' to restart from partial results '''
    global lastRequestTime 
    lastRequestTime = -5      # in seconds
    delay =5.1 # robots.txt requires delay >= 5  seconds
    
    directory = 'C:\\users\\Moi2\\Documents\\PYTHON_travail\\PROJETS_WebScraping_WebAPI_ParseXML_HTML\\'
    filename = 'MECscrapping_july2018.json'
    siteEng = 'http://www.mec.ca/en/'
    siteFr  = 'http://www.mec.ca/fr/'
    website ={'Eng':siteEng, 'Fr':siteFr}
        
    ###  result = [categoryNames, categoryLinks, itemNames, itemLinks, items, soupBug]    
    result = openResults(directory+filename)
    filename = filename +'_2'  # we modify the filename just in case... 

    ### assuming the loops are going:  for lang= Eng, Fr; for catName ...
    ### the point to be restart is described by (lang0, catNb0), where catNb0 = index of catName in categoryNames[lang]
    categoryNames =result[0]
    lang0 = 'Fr'
    catNb0=1  # the first index being 0
    catName0 = categoryNames[lang0][catNb0]
    # it means everything is already done before lang ==lang0 and catNb>catNb0
      
    print 'we start from %s, %s.'%(lang0, catName0)  
    for lang in ['Fr','Eng']:        
        for catNb,catName in list(enumerate(categoryNames[lang])):
            
            ### the jump condition, ( i.e. everything before is done),  is :
            if lang0=='Eng' :  jumpCondition =  ( lang =='Fr' or catNb < catNb0 )
            elif lang0=='Fr':  jumpCondition =  ( lang =='Fr' and catNb < catNb0 )
            if jumpCondition: continue          
            
            print '\n%s, %s :  '%(lang, catName)            
            ### given a category and a language, extract a list of all item links and names from category pages
            ### fill itemNames[lang][catName], itemLinks[lang][catName], 
            ### update and save result in filename.json
            result1 = extractItemListLoop(lang,catName, website, delay, filename, result)

            ### given a category and a language, for each item in the list, open the item webpage and extract its details 
            ###  fill items[lang][catName]  , update and save result = [categoryNames, categoryLinks, itemNames, itemLinks, items, soupBug] in filename.json
            result = extractItemLoop(lang, catName,  website, delay, filename, result1)
        
if __name__== "__main__":
    #main()
    
    
    restart()
    
    