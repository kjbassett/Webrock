import asyncpraw
from data_access.dao_manager import dao_manager
from utils.project_utilities import get_key

from ..decorator import plugin

reddit_dao = dao_manager.get_dao("Reddit")


async def fetch_posts_and_comments(reddit, subreddits):
    subreddits = await reddit.subreddit("+".join(subreddits))
    i = 0
    async for submission in subreddits.top(time_filter="hour"):
        i += 1
        print(i)
        data = [submission]

        comments = await submission.comments()  # get first layer of comments
        await comments.replace_more(limit=None)  # get next layer of comments
        for top_level_comment in submission.comments:
            data.append(top_level_comment)
            for second_level_comment in top_level_comment.replies:
                data.append(second_level_comment)

        # Save submission data to the database
        await save_data(data)


async def save_data(data):
    params = []
    await data[0].subreddit.load()
    sub = data[0].subreddit.display_name
    for i, d in enumerate(data):
        if i == 0:
            d.body = (
                d.selftext
                if d.selftext
                else (
                    d.url if d.url.endswith((".jpg", ".jpeg", ".png", ".gif")) else ""
                )
            )
            d.parent_id = None
        if d.author:
            await d.author.load()
            author_id = d.author.id if d.author else None
        else:
            author_id = None
        params.append((d.id, sub, d.parent_id, None, d.body, author_id, d.score))

    await reddit_dao.insert(params, on_conflict="UPDATE")


@plugin()
async def main():
    """
    test docstring
    """
    subs = ["wallstreetbets", "stocks", "StockMarket", "investing"]

    reddit = asyncpraw.Reddit(
        client_id=get_key("reddit_id"),
        client_secret=get_key("reddit_secret"),
        password=get_key("reddit_password"),
        user_agent="stonks",
        username=get_key("reddit_username"),
    )

    await fetch_posts_and_comments(reddit, subs)
    await reddit.close()


# re.findall(r"(?<=\$)\w+|[A-Z]{3,6}", text):  # magic
