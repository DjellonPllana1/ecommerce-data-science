"""Cluster naming, profiles, and business recommendations."""

from __future__ import annotations

import pandas as pd


def assign_cluster_names(profile: pd.DataFrame) -> dict[int,str]:
    """Assign unique names after inspecting actual cluster profiles."""
    if len(profile)==2 and profile.repeat_customer_rate.max()>.9 and profile.repeat_customer_rate.min()<.1:
        repeat_id=int(profile.loc[profile.repeat_customer_rate.idxmax(),"cluster_id"])
        one_time_id=int(profile.loc[profile.repeat_customer_rate.idxmin(),"cluster_id"])
        return {repeat_id:"Repeat High-Value Customers",one_time_id:"One-Time Customers"}
    remaining=set(profile.cluster_id.astype(int)); names={}
    def take(cluster_id,name):
        cluster_id=int(cluster_id)
        if cluster_id in remaining: names[cluster_id]=name; remaining.remove(cluster_id)
    take(profile.loc[profile.mean_monetary.idxmax(),"cluster_id"],"High-Value Customers")
    if remaining: take(profile[profile.cluster_id.isin(remaining)].sort_values(["repeat_customer_rate","median_frequency"],ascending=False).iloc[0].cluster_id,"Repeat Customers")
    if remaining: take(profile[profile.cluster_id.isin(remaining)].sort_values("median_recency").iloc[0].cluster_id,"Recent Customers")
    if remaining: take(profile[profile.cluster_id.isin(remaining)].sort_values("median_recency",ascending=False).iloc[0].cluster_id,"Hibernating Customers")
    for number,cluster_id in enumerate(sorted(remaining),1): names[int(cluster_id)]=f"Occasional Customers {number}"
    return names


def build_cluster_profiles(frame: pd.DataFrame) -> tuple[pd.DataFrame,dict[int,str]]:
    total_revenue=frame.monetary.sum()
    profile=frame.groupby("cluster_id").agg(customer_count=("customer_unique_id","size"),median_recency=("recency","median"),median_frequency=("frequency","median"),median_monetary=("monetary","median"),mean_monetary=("monetary","mean"),total_revenue=("monetary","sum"),repeat_customer_rate=("frequency",lambda x:x.gt(1).mean())).reset_index()
    profile["customer_percentage"]=100*profile.customer_count/len(frame); profile["revenue_share"]=100*profile.total_revenue/total_revenue
    states=frame.groupby("cluster_id")["customer_state"].apply(lambda x:", ".join(x.value_counts().head(3).index)).rename("top_customer_states").reset_index(); profile=profile.merge(states,on="cluster_id")
    names=assign_cluster_names(profile); profile["cluster_name"]=profile.cluster_id.map(names)
    return profile.sort_values("cluster_id"),names


RECOMMENDATIONS={
    "Repeat High-Value Customers":"Protect this scarce repeat group with recognition, priority service, and personalized cross-sell offers.",
    "One-Time Customers":"Use onboarding and carefully tested second-purchase prompts, segmented further by rule-based recency and value.",
    "High-Value Customers":"Protect with priority support, loyalty recognition, and relevant premium cross-sell offers.",
    "Repeat Customers":"Reward repeat behavior and encourage broader category adoption through personalized offers.",
    "Recent Customers":"Use onboarding and a time-bound second-purchase campaign while the first order is fresh.",
    "Hibernating Customers":"Run selective reactivation tests and suppress outreach when response economics are weak.",
    "Occasional Customers 1":"Use low-cost lifecycle messaging and category-relevant reminders.",
    "Occasional Customers 2":"Test differentiated incentives while monitoring incremental margin.",
}
