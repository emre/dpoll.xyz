import copy
import uuid
from datetime import timedelta

from dateutil.parser import parse
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.views import auth_logout
from django.core.paginator import Paginator
from django.db.models import Count
from django.http import Http404
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.utils.timezone import now
from steemconnect.client import Client
from steemconnect.operations import Comment

from base.utils import add_tz_info
from .models import Question, Choice, User
from .utils import (
    get_sc_client, get_comment_options, get_top_dpollers,
    get_top_voters, validate_input, add_or_get_question, add_choices,
    get_comment, fetch_poll_data)

TEAM_MEMBERS  = [
        {
            "username": "emrebeyler",
            "title": "Developer",
        },
        {
            "username": "isnochys",
            "title": "Joker",
        },
        {
            "username": "bluerobo",
            "title": "Curator",
        },
        {
            "username": "tolgahanuzun",
            "title": "Developer",
        }
    ]


def index(request):
    questions = Question.objects.all().order_by("-id")
    paginator = Paginator(questions, 10)

    page = request.GET.get('page')
    polls = paginator.get_page(page)

    stats = {
        'poll_count': Question.objects.all().count(),
        'vote_count': Choice.objects.aggregate(
            total_votes=Count('voted_users'))["total_votes"],
        'user_count': User.objects.all().count(),
        'top_dpollers': get_top_dpollers(),
        'top_voters': get_top_voters(),
    }

    return render(request, "index.html", {"polls": polls, "stats": stats})


def sc_login(request):
    if 'access_token' not in request.GET:
        login_url = get_sc_client().get_login_url(
            redirect_uri=settings.SC_REDIRECT_URI,
            scope="login,comment,comment_options",
        )
        return redirect(login_url)

    user = authenticate(access_token=request.GET.get("access_token"))

    if user is not None:
        if user.is_active:
            login(request, user)
            request.session["sc_token"] = request.GET.get("access_token")
            if request.session.get("initial_referer"):
                return redirect(request.session["initial_referer"])
            return redirect("/")
        else:
            return HttpResponse("Account is disabled.")
    else:
        return HttpResponse("Invalid login details.")


def sc_logout(request):
    auth_logout(request)
    return redirect("/")


def create_poll(request):
    if not request.user.is_authenticated:
        return redirect('login')

    if request.method == 'POST':
        form_data = copy.copy(request.POST)

        if 'sc_token' not in request.session:
            return redirect("/")

        error, question, choices, expire_at, permlink, days, tags = validate_input(
            request)

        if error:
            form_data.update({
                "answers": request.POST.getlist("answers[]"),
                "expire_at": request.POST.get("expire-at"),
                "reward_option": request.POST.get("reward-option")
            })
            return render(request, "add.html", {"form_data": form_data})

        if (Question.objects.filter(
                permlink=permlink, username=request.user)).exists():
            messages.add_message(
                request,
                messages.ERROR,
                "You have already a similar poll."
            )
            return redirect('create-poll')

        # add question
        question = add_or_get_question(
            request,
            question,
            permlink,
            days
        )
        question.save()

        # add answers attached to it
        add_choices(question, choices)

        # send it to the steem blockchain
        sc_client = Client(access_token=request.session.get("sc_token"))
        comment = get_comment(request, question, choices, permlink, tags)
        comment_options = get_comment_options(
            comment,
            reward_option=request.POST.get("reward-option")
        )
        if not settings.BROADCAST_TO_BLOCKCHAIN:
            resp = {}
        else:
            resp = sc_client.broadcast([
                comment.to_operation_structure(),
                comment_options.to_operation_structure(),
            ])

        if 'error' in resp:
            if 'The token has invalid role' in resp.get("error_description"):
                # expired token
                auth_logout(request)
                return redirect('login')

            messages.add_message(
                request,
                messages.ERROR,
                resp.get("error_description", "error")
            )
            question.delete()
            return redirect('create-poll')

        return redirect('detail', question.username, question.permlink)

    return render(request, "add.html")


def edit_poll(request, author, permlink):
    if not request.user.is_authenticated:
        return redirect('login')

    try:
        poll = Question.objects.get(
            permlink=permlink,
            username=author,
        )
    except Question.DoesNotExist:
        raise Http404

    if author != request.user.username:
        raise Http404

    if request.method == "GET":
        poll_data = fetch_poll_data(poll.username, poll.permlink)
        tags = poll_data.get("tags", [])
        tags = [tag for tag in tags if tag not in settings.DEFAULT_TAGS]
        form_data = {
            "question": poll.text,
            "description": poll.description,
            "answers": [c.text for c in Choice.objects.filter(question=poll)],
            "expire_at": poll.expire_at_humanized,
            "tags": ",".join(tags),
        }

    if request.method == 'POST':
        form_data = copy.copy(request.POST)

        if 'sc_token' not in request.session:
            return redirect("/")

        error, question, choices, expire_at, _, days, tags = validate_input(
            request)
        if tags:
            tags = settings.DEFAULT_TAGS + tags
        else:
            tags = settings.DEFAULT_TAGS

        permlink = poll.permlink

        if error:
            form_data.update({
                "answers": request.POST.getlist("answers[]"),
                "expire_at": request.POST.get("expire-at"),
            })
            return render(request, "edit.html", {"form_data": form_data})

        # add question
        question = add_or_get_question(
            request,
            question,
            permlink,
            days
        )
        question.save()

        # add answers attached to it
        add_choices(question, choices, flush=True)

        # send it to the steem blockchain
        sc_client = Client(access_token=request.session.get("sc_token"))
        comment = get_comment(request, question, choices, permlink, tags=tags)
        if not settings.BROADCAST_TO_BLOCKCHAIN:
            resp = {}
        else:
            resp = sc_client.broadcast([
                comment.to_operation_structure(),
            ])

        if 'error' in resp:
            if 'The token has invalid role' in resp.get("error_description"):
                # expired token
                auth_logout(request)
                return redirect('login')

            messages.add_message(
                request,
                messages.ERROR,
                resp.get("error_description", "error")
            )
            question.delete()
            return redirect('edit', args=(author, permlink))

        return redirect('detail', question.username, question.permlink)

    return render(request, "edit.html", {
        "form_data": form_data,
    })


def detail(request, user, permlink):
    try:
        poll = Question.objects.get(username=user, permlink=permlink)
    except Question.DoesNotExist:
        raise Http404

    choices = list(Choice.objects.filter(question=poll))
    all_votes = sum([c.votes for c in choices])
    choice_list = []
    selected_different_choices = 0
    for choice in choices:
        choice_data = choice
        if choice.votes:
            choice_data.percent = round(100 * choice.votes / all_votes, 2)
            selected_different_choices += 1
        else:
            choice_data.percent = 0
        choice_list.append(choice_data)
    sorted_choice_list = copy.deepcopy(choice_list)
    sorted_choice_list.sort(key=lambda x: x.percent, reverse=True)

    user_vote = Choice.objects.filter(
        voted_users__username=request.user.username,
        question=poll,
    )
    if len(user_vote):
        user_vote = user_vote[0]
    else:
        user_vote = None

    return render(request, "poll_detail.html", {
        "poll": poll,
        "choices": choice_list,
        "sorted_choices": sorted_choice_list,
        "total_votes": all_votes,
        "user_vote": user_vote,
        "all_votes": all_votes,
        "show_bars": selected_different_choices > 1
    })


def vote(request, user, permlink):
    if request.method != "POST":
        raise Http404

    # django admin users should not be able to vote.
    if not request.session.get("sc_token"):
        redirect('logout')

    try:
        poll = Question.objects.get(username=user, permlink=permlink)
    except Question.DoesNotExist:
        raise Http404

    if not request.user.is_authenticated:
        return redirect('login')

    choice_id = request.POST.get("choice-id")
    additional_thoughts = request.POST.get("vote-comment", "")

    if not choice_id:
        raise Http404

    if Choice.objects.filter(
            voted_users__username=request.user,
            question=poll).exists():
        messages.add_message(
            request,
            messages.ERROR,
            "You have already voted for this poll!"
        )

        return redirect("detail", poll.username, poll.permlink)

    if not poll.is_votable():
        messages.add_message(
            request,
            messages.ERROR,
            "This poll is expired!"
        )
        return redirect("detail", poll.username, poll.permlink)

    try:
        choice = Choice.objects.get(pk=int(choice_id))
    except Choice.DoesNotExist:
        raise Http404

    choice.voted_users.add(request.user)

    # send it to the steem blockchain
    sc_client = Client(access_token=request.session.get("sc_token"))
    choice_text = choice.text.strip()
    body = f"Voted for *{choice_text}*."
    if additional_thoughts:
        body += f"\n\n{additional_thoughts}"
    comment = Comment(
        author=request.user.username,
        permlink=str(uuid.uuid4()),
        body=body,
        parent_author=poll.username,
        parent_permlink=poll.permlink,
        json_metadata={
            "tags": settings.DEFAULT_TAGS,
            "app": f"dpoll/{settings.DPOLL_APP_VERSION}",
            "content_type": "poll_vote",
            "vote": choice.text
        }
    )

    comment_options = get_comment_options(comment)
    if not settings.BROADCAST_TO_BLOCKCHAIN:
        resp = {}
    else:
        resp = sc_client.broadcast([
            comment.to_operation_structure(),
            comment_options.to_operation_structure(),
        ])

    if 'error' in resp:
        messages.add_message(
            request,
            messages.ERROR,
            resp.get("error_description", "error")
        )
        choice.voted_users.remove(request.user)

        return redirect("detail", poll.username, poll.permlink)

    messages.add_message(
        request,
        messages.SUCCESS,
        "You have successfully voted!"
    )

    return redirect("detail", poll.username, poll.permlink)


def profile(request, user):
    try:
        user = User.objects.get(username=user)
    except User.DoesNotExist:
        raise Http404

    polls = user.polls_created
    votes = user.votes_casted
    poll_count = len(polls)
    vote_count = len(votes)

    return render(request, "profile.html", {
        "user": user,
        "polls": polls,
        "votes": votes,
        "poll_count": poll_count,
        "vote_count": vote_count,
    })


def team(request):
    return render(request, "team.html", {"team_members": TEAM_MEMBERS})


def polls_by_vote_count(request):
    end_time = now()
    start_time = now() - timedelta(days=7)
    if request.GET.get("start_time"):
        try:
            start_time = add_tz_info(parse(request.GET.get("start_time")))
        except Exception as e:
            pass
    if request.GET.get("end_time"):
        try:
            end_time = add_tz_info(parse(request.GET.get("end_time")))
        except Exception as e:
            pass

    polls = []
    questions = Question.objects.filter(
            created_at__gt=start_time,
            created_at__lt=end_time)
    if request.GET.get("exclude_team_members"):
        questions = questions.exclude(username__in=settings.TEAM_MEMBERS)

    for question in questions:
        vote_count = 0
        for choice in question.choices.all():
            vote_count += choice.voted_users.all().count()
        polls.append({"vote_count": vote_count, "poll": question})

    polls = sorted(polls, key=lambda x: x["vote_count"], reverse=True)

    return render(request, "polls_by_vote.html", {
        "polls": polls, "start_time": start_time, "end_time": end_time})
