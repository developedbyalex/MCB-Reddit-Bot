import praw
import time
import logging
from datetime import datetime, UTC, timedelta
from prawcore.exceptions import Forbidden, NotFound
import requests
import json

WEBHOOK_URL = "WEBHOOK_URL"

def send_to_discord(title, description, color=0x00ff00, fields=None):
    embed = {
        "title": title,
        "description": description,
        "color": color,
        "timestamp": datetime.now(UTC).isoformat()
    }
    
    if fields:
        embed["fields"] = fields

    data = {
        "embeds": [embed]
    }
    
    try:
        requests.post(WEBHOOK_URL, json=data)
    except Exception as e:
        print(f"Failed to send to Discord: {e}")

def report_post(submission):
    try:
        submission.report("User has posted within the last 14 days")
        return True
    except Exception as e:
        send_to_discord(
            "Report Error",
            f"Failed to report post: {str(e)}",
            color=0xff0000
        )
        return False

reddit = praw.Reddit(
    client_id="YOUR_CLIENT_ID",
    client_secret="YOUR_CLIENT_SECRET",
    user_agent="YOUR_USER_AGENT",
    username="YOUR_REDDIT_USERNAME",
    password="YOUR_REDDIT_PASSWORD"
)

def check_user_history(username, current_post):  # Changed to accept submission object
    try:
        user = reddit.redditor(username)
        restricted_subs = {'mcservers', 'minecraftserver'}
        cutoff_date = datetime.now(UTC) - timedelta(days=14)
        
        for submission in user.submissions.new(limit=100):
            if submission.id == current_post.id:
                continue
            
            post_date = datetime.fromtimestamp(submission.created_utc, UTC)
            
            if submission.subreddit.display_name.lower() in restricted_subs:
                send_to_discord(
                    "Restricted Subreddit Post",
                    f"User has posted in a restricted subreddit",
                    color=0xffa500,
                    fields=[
                        {"name": "User", "value": f"[{username}](https://reddit.com/u/{username})", "inline": True},
                        {"name": "Restricted Subreddit", "value": submission.subreddit.display_name, "inline": True},
                        {"name": "New Post", "value": f"[View Post]({current_post.url})", "inline": False},
                        {"name": "Other Subreddit Post", "value": f"[View Post](https://reddit.com{submission.permalink})", "inline": False}
                    ]
                )
                return True
            
            if submission.subreddit.display_name.lower() == 'minecraftbuddies' and post_date > cutoff_date:
                # Report the current post
                report_post(current_post)
                
                send_to_discord(
                    "Recent Post Detection",
                    f"User has posted in MinecraftBuddies within 14 days",
                    color=0xffa500,
                    fields=[
                        {"name": "User", "value": f"[{username}](https://reddit.com/u/{username})", "inline": True},
                        {"name": "Previous Post Date", "value": post_date.strftime("%Y-%m-%d"), "inline": True},
                        {"name": "New Post", "value": f"[View Post]({current_post.url})", "inline": False},
                        {"name": "Previous Post", "value": f"[View Post](https://reddit.com{submission.permalink})", "inline": False}
                    ]
                )
                return True

    except (Forbidden, NotFound):
        send_to_discord(
            "Warning",
            f"Could not access history for user {username}",
            color=0xffff00
        )
        return False
    return False

def monitor_submissions():
    subreddit = reddit.subreddit('MinecraftBuddies')
    send_to_discord("Bot Status", "Starting submission monitor", color=0x00ff00)
    
    for submission in subreddit.stream.submissions(skip_existing=True):
        try:
            send_to_discord(
                "New Submission",
                f"New post in MinecraftBuddies",
                fields=[
                    {"name": "Post ID", "value": submission.id, "inline": True},
                    {"name": "Author", "value": f"[{submission.author.name}](https://reddit.com/u/{submission.author.name})", "inline": True},
                    {"name": "Title", "value": submission.title[:100], "inline": False},
                    {"name": "Post URL", "value": f"[View Post]({submission.url})", "inline": False}
                ]
            )
            
            check_user_history(submission.author.name, submission)  # Pass the submission object
            
            time.sleep(2)
            
        except Exception as e:
            send_to_discord(
                "Error",
                f"Error processing submission {submission.id}: {str(e)}",
                color=0xff0000
            )
            continue

if __name__ == "__main__":
    print("Bot starting... Check Discord for detailed operation information.")
    send_to_discord("Bot Status", "Bot starting up", color=0x00ff00)
    
    while True:
        try:
            monitor_submissions()
        except Exception as e:
            send_to_discord(
                "Critical Error",
                f"Main loop error: {str(e)}",
                color=0xff0000
            )
            time.sleep(60)