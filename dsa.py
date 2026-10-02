
import heapq
from bisect import bisect_left
from collections import defaultdict, deque

def build_skill_index(candidates):
    index = defaultdict(set)
    for c in candidates:
        for skill in c["skills"]: index[skill.lower()].add(c["id"])
    return index

def rank_candidates(candidates, required_skills, min_experience=0):
    required={s.lower() for s in required_skills}; heap=[]
    for c in candidates:
        skills={s.lower() for s in c["skills"]}
        coverage=len(skills & required)/max(1,len(required))
        exp_score=min(c["experience"]/10,1.0)
        score=.7*coverage+.3*exp_score
        if c["experience"]>=min_experience:
            heapq.heappush(heap,(-score,c["id"],c["name"],score))
    return [heapq.heappop(heap) for _ in range(len(heap))]

def binary_search(values,target):
    i=bisect_left(values,target)
    return i if i<len(values) and values[i]==target else -1

def merge_sort(values):
    if len(values)<=1:return values[:]
    m=len(values)//2;l=merge_sort(values[:m]);r=merge_sort(values[m:])
    out=[];i=j=0
    while i<len(l) and j<len(r):
        if l[i]<=r[j]:out.append(l[i]);i+=1
        else:out.append(r[j]);j+=1
    return out+l[i:]+r[j:]

def sliding_window_counts(events,window=3):
    q=deque(); counts=defaultdict(int); result=[]
    for e in events:
        q.append(e);counts[e]+=1
        while len(q)>window: counts[q.popleft()]-=1
        result.append(dict(counts))
    return result
