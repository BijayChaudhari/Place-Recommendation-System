from django.shortcuts import render,HttpResponseRedirect
from django.contrib.auth import authenticate,login,logout,update_session_auth_hash
from django.contrib.auth.models import User,Group
from .forms import SignUpForm,AddPlaceForm,LoginForm,AddRatingForm
from .models import Place,Rating
from django.contrib import messages
import pandas as pd
from math import sqrt
import numpy as np
import matplotlib.pyplot as plt
from math import ceil

def filterPlaceByCategories():
     #filtering by categories
    allPlaces=[]
    categoriesPlace= Place.objects.values('categories', 'id')
    categories= {item["categories"] for item in categoriesPlace}
    for category in categories:
        place=Place.objects.filter(categories=category)
        print(place)
        n = len(place)
        nSlides = n // 4 + ceil((n / 4) - (n // 4))
        allPlaces.append([place, range(1, nSlides), nSlides])
    params={'allPlaces':allPlaces }
    return params


def generateRecommendation(request):
    place=Place.objects.all()
    rating=Rating.objects.all()
    x=[] 
    y=[]
    A=[]
    B=[]
    C=[]
    D=[]
    #Place Data Frames
    for item in place:
        x=[item.id,item.title,item.placeweather,item.image.url,item.categories] 
        y+=[x]
    places_df = pd.DataFrame(y,columns=['placeId','title','placeweather','image','categories'])
    print("Places DataFrame")
    print(places_df)
    print(places_df.dtypes)
#Rating Data Frames
    print(rating)
    for item in rating:
        A=[item.user.id,item.place,item.rating]
        B+=[A]
    rating_df=pd.DataFrame(B,columns=['userId','placeId','rating'])
    print("Rating data Frame")
    rating_df['userId']=rating_df['userId'].astype(str).astype(np.int64)
    rating_df['placeId']=rating_df['placeId'].astype(str).astype(np.int64)
    rating_df['rating']=rating_df['rating'].astype(str).astype(float)
    print(rating_df)
    print(rating_df.dtypes)
    if request.user.is_authenticated:
        userid=request.user.id
        #select related is join statement in django.It looks for foreign key and join the table
        userInput=Rating.objects.select_related('place').filter(user=userid)
        if userInput.count()== 0:
            recommenderQuery=None
            userInput=None
        else:
            for item in userInput:
                C=[item.place.title,item.rating]
                D+=[C]
            inputPlaces=pd.DataFrame(D,columns=['title','rating'])
            print("Visited Places by user dataframe")
            inputPlaces['rating']=inputPlaces['rating'].astype(str).astype(float)
            print(inputPlaces.dtypes)

            #Filtering out the places by title
            inputId = places_df[places_df['title'].isin(inputPlaces['title'].tolist())]
            #Then merging it so we can get the placeId. It's implicitly merging it by title.
            inputPlaces = pd.merge(inputId,inputPlaces)
            # #Dropping information we won't use from the input dataframe
            # inputPlaces = inputPlaces.drop('year', 1)
            #Final input dataframe
            #If a movie you added in above isn't here, then it might not be in the original 
            #dataframe or it might spelled differently, please check capitalisation.
            print(inputPlaces)

            #Filtering out users that have watched places that the input has watched and storing it
            userSubset = rating_df[rating_df['placeId'].isin(inputPlaces['placeId'].tolist())]
            print(userSubset.head())

            #Groupby creates several sub dataframes where they all have the same value in the column specified as the parameter
            userSubsetGroup = userSubset.groupby(['userId'])
            
            #print(userSubsetGroup.get_group(7))

            #Sorting it so users with place most in common with the input will have priority
            userSubsetGroup = sorted(userSubsetGroup,  key=lambda x: len(x[1]), reverse=True)

            print(userSubsetGroup[0:])


            userSubsetGroup = userSubsetGroup[0:]

            #Store the Pearson Correlation in a dictionary, where the key is the user Id and the value is the coefficient
            pearsonCorrelationDict = {}

            #For every user group in our subset
            for name, group in userSubsetGroup:
                #Let's start by sorting the input and current user group so the values aren't mixed up later on
                group = group.sort_values(by='placeId')
                inputPlaces = inputPlaces.sort_values(by='placeId')
                #Get the N for the formula
                nRatings = len(group)
                #Get the review scores for the places that they both have in common
                temp_df = inputPlaces[inputPlaces['placeId'].isin(group['placeId'].tolist())]
                #And then store them in a temporary buffer variable in a list format to facilitate future calculations
                tempRatingList = temp_df['rating'].tolist()
                #Let's also put the current user group reviews in a list format
                tempGroupList = group['rating'].tolist()
                #Now let's calculate the pearson correlation between two users, so called, x and y
                Sxx = sum([i**2 for i in tempRatingList]) - pow(sum(tempRatingList),2)/float(nRatings)
                Syy = sum([i**2 for i in tempGroupList]) - pow(sum(tempGroupList),2)/float(nRatings)
                Sxy = sum( i*j for i, j in zip(tempRatingList, tempGroupList)) - sum(tempRatingList)*sum(tempGroupList)/float(nRatings)
                

                #If the denominator is different than zero, then divide, else, 0 correlation.
                if Sxx != 0 and Syy != 0:
                    pearsonCorrelationDict[name] = Sxy/sqrt(Sxx*Syy)
                else:
                    pearsonCorrelationDict[name] = 0

            print(pearsonCorrelationDict.items())

            pearsonDF = pd.DataFrame.from_dict(pearsonCorrelationDict, orient='index')
            pearsonDF.columns = ['similarityIndex']
            pearsonDF['userId'] = pearsonDF.index
            pearsonDF.index = range(len(pearsonDF))
            print(pearsonDF.head())

            topUsers=pearsonDF.sort_values(by='similarityIndex', ascending=False)[0:]
            print(topUsers.head())

            topUsersRating = pd.concat([topUsers,rating_df], axis=1, join='inner')
           
            topUsersRating.head()

            #Multiplies the similarity by the user's ratings
            topUsersRating['weightedRating'] = topUsersRating['similarityIndex']*topUsersRating['rating']
            topUsersRating.head()
            

            #Applies a sum to the topUsers after grouping it up by userId
            tempTopUsersRating = topUsersRating.groupby('placeId').sum()[['similarityIndex','weightedRating']]
            tempTopUsersRating.columns = ['sum_similarityIndex','sum_weightedRating']
            tempTopUsersRating.head()

            #Creates an empty dataframe
            recommendation_df = pd.DataFrame()
            #Now we take the weighted average
            recommendation_df['weighted average recommendation score'] = tempTopUsersRating['sum_weightedRating']/tempTopUsersRating['sum_similarityIndex']
            recommendation_df['placeId'] = tempTopUsersRating.index
            recommendation_df.head()

            recommendation_df = recommendation_df.sort_values(by='weighted average recommendation score', ascending=False)
            recommender=places_df.loc[places_df['placeId'].isin(recommendation_df.head(5)['placeId'].tolist())]
            print(recommender)
            return recommender.to_dict('records')
            

def signup(request):
    if not request.user.is_authenticated:
        if request.method=='POST':
            fm=SignUpForm(request.POST)
            if fm.is_valid():
                user=fm.save()
                group=Group.objects.get(name='Editor')
                user.groups.add(group)
                messages.success(request,'Account Created Successfully!!!')
        else:
            if not request.user.is_authenticated:
                fm=SignUpForm()
        return render(request,'PlaceRecommendation/signup.html',{'form':fm})
    else:
        return HttpResponseRedirect('/home/')


def user_login(request):
    if not request.user.is_authenticated:
        if request.method=='POST':
            fm=LoginForm(request=request,data=request.POST)
            if fm.is_valid():
                uname=fm.cleaned_data['username']
                upass=fm.cleaned_data['password']
                user=authenticate(username=uname,password=upass)
                if user is not None:
                    login(request,user)
                    messages.success(request,'Logged in Successfully!!')
                    return HttpResponseRedirect('/dashboard/')
        else:
            fm=LoginForm()
        return render(request,'PlaceRecommendation/login.html',{'form':fm})
    else:
        return HttpResponseRedirect('/dashboard/')



def home(request):
    params=filterPlaceByCategories()
    params['recommended']=generateRecommendation(request)
    return render(request,'PlaceRecommendation/home.html',params)

def addplace(request):
    if request.user.is_authenticated:
        if request.method=='POST':
            fm=AddPlaceForm(request.POST,request.FILES)
            if fm.is_valid():
                fm.save()
                messages.success(request,'Place Added Successfully!!!')
        else:
            fm=AddPlaceForm()
        return render(request,'PlaceRecommendation/addplace.html',{'form':fm})
    else:
        return HttpResponseRedirect('/login/')


def dashboard(request):
    if request.user.is_authenticated: 
        params=filterPlaceByCategories()
        params['user']=request.user
        if request.method=='POST':
            userid=request.POST.get('userid')
            placeid=request.POST.get('placeid')
            place=Place.objects.all()
            u=User.objects.get(pk=userid)
            m=Place.objects.get(pk=placeid)
            rfm=AddRatingForm(request.POST)
            params['rform']=rfm
            if rfm.is_valid():
                rat=rfm.cleaned_data['rating']
                count=Rating.objects.filter(user=u,place=m).count()
                if(count>0):
                    messages.warning(request,'You have already submitted your review!!')
                    return render(request,'PlaceRecommendation/dashboard.html',params)
                action=Rating(user=u,place=m,rating=rat)
                action.save()
                messages.success(request,'You have submitted'+' '+rat+' '+"star")
            return render(request,'PlaceRecommendation/dashboard.html',params)
        else:
            #print(request.user.id)
            rfm=AddRatingForm()
            params['rform']=rfm
            place=Place.objects.all()
            return render(request,'PlaceRecommendation/dashboard.html',params)
    else:
        return HttpResponseRedirect('/login/')



def user_logout(request):
    if request.user.is_authenticated:
        logout(request)
        return HttpResponseRedirect('/login/')

def profile(request):
    if request.user.is_authenticated:
        #"select sum(rating) from Rating where user=request.user.id"
        r=Rating.objects.filter(user=request.user.id)
        totalReview=0
        for item in r:
            totalReview+=int(item.rating)
        #select count(*) from Rating where user=request.user.id"
        totalplacesvisited=Rating.objects.filter(user=request.user.id).count()
        return render(request,'PlaceRecommendation/profile.html',{'totalReview':totalReview,'totalplacesvisited':totalplacesvisited})
    else:
        return HttpResponseRedirect('/login/')

