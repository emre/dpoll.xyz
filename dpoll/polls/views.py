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
from prettytable import PrettyTable

from base.utils import add_tz_info
from .models import Question, Choice, User, VoteAudit
from .utils import (
    get_sc_client, get_comment_options, get_top_dpollers,
    get_top_voters, validate_input, add_or_get_question, add_choices,
    get_comment, fetch_poll_data, sanitize_filter_value)

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

    query_params = {
        "expire_at__gt": now(),
    }
    # ordering by new, trending, or promoted.
    order_by = "-id"
    if request.GET.get("order"):
        if request.GET.get("order") == "trending":
            order_by = "-voter_count"
        elif request.GET.get("order") == "promoted":
            order_by = "-promotion_amount"
            query_params.update({
                "promotion_amount__gt": float(0.000),
            })

    questions = Question.objects.filter(**query_params).order_by(order_by)
    paginator = Paginator(questions, 10)

    promoted_polls = Question.objects.filter(
        expire_at__gt=now(),
        promotion_amount__gt=float(0.000),
    ).order_by("-promotion_amount")

    if len(promoted_polls):
        promoted_poll = promoted_polls[0]
    else:
        promoted_poll = None

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

    return render(request, "index.html", {
        "polls": polls, "stats": stats, "promoted_poll": promoted_poll})


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

        error, question, choices, expire_at, permlink, days, tags, \
            allow_multiple_choices = validate_input(request)

        if error:
            form_data.update({
                "answers": request.POST.getlist("answers[]"),
                "expire_at": request.POST.get("expire-at"),
                "reward_option": request.POST.get("reward-option"),
                "allow_multiple_choices": request.POST.get(
                    "allow-multiple-choices"),
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
            days,
            allow_multiple_choices
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
            "allow_multiple_choices": poll.allow_multiple_choices
        }

    if request.method == 'POST':
        form_data = copy.copy(request.POST)

        if 'sc_token' not in request.session:
            return redirect("/")

        error, question, choices, expire_at, _, days, tags, \
            allow_multiple_choices = validate_input(request)
        if tags:
            tags = settings.DEFAULT_TAGS + tags
        else:
            tags = settings.DEFAULT_TAGS

        permlink = poll.permlink

        if error:
            form_data.update({
                "answers": request.POST.getlist("answers[]"),
                "expire_at": request.POST.get("expire-at"),
                "allow_multiple_choices": request.POST.get(
                    "allow-multiple-choices"),
            })
            return render(request, "edit.html", {"form_data": form_data})

        # add question
        question = add_or_get_question(
            request,
            question,
            permlink,
            days,
            allow_multiple_choices
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

    if 'after_promotion' in request.GET:
        messages.add_message(
            request,
            messages.SUCCESS,
            "Thanks for the promotion. Transfer will be picked up by our systems between 2 and 5 minutes."
        )

    try:
        poll = Question.objects.get(username=user, permlink=permlink)
    except Question.DoesNotExist:
        raise Http404

    rep = sanitize_filter_value(request.GET.get("rep"))
    sp = sanitize_filter_value(request.GET.get("sp"))
    age = sanitize_filter_value(request.GET.get("age"))
    post_count = sanitize_filter_value(request.GET.get("post_count"))
    needs_filtering = bool(rep or sp or age or post_count)

    choices = list(Choice.objects.filter(question=poll))

    if needs_filtering:
        all_votes = sum(
            [c.filtered_vote_count(rep, age, post_count, sp) for c in choices])
    else:
        all_votes = sum([c.votes for c in choices])
    choice_list = []
    selected_different_choices = 0
    for choice in choices:
        choice_data = choice
        if choice.votes:
            if needs_filtering:
                choice_data.vote_count, choice_data.voters = choice.filtered_vote_count(
                    rep, age, post_count, sp, return_users=True)
                if choice_data.vote_count == 0:
                    choice_data.percent = 0
                else:
                    choice_data.percent = round(100 * choice_data.vote_count / all_votes, 2)
            else:
                choice_data.vote_count = choice.votes
                choice_data.percent = round(100 * choice_data.vote_count / all_votes, 2)
                choice_data.voters = choice.voted_users.all()
            selected_different_choices += 1
        else:
            choice_data.percent = 0
        choice_list.append(choice_data)

    sorted_choice_list = copy.deepcopy(choice_list)
    sorted_choice_list.sort(key=lambda x: x.percent, reverse=True)

    user_votes = Choice.objects.filter(
        voted_users__username=request.user.username,
        question=poll,
    ).values_list('id', flat=True)

    if 'audit' in request.GET:
        # Return a .xls file includes blockchain references and votes
        data = PrettyTable()
        data.field_names = ["Choice", "Voter", "Transaction ID", "Block num"]
        for choice in sorted_choice_list:
            if hasattr(choice, 'voters'):
                for user in choice.voters:
                    try:
                        audit = VoteAudit.objects.get(
                            question=poll,
                            voter=user,
                        )
                        data.add_row(
                            [choice.text, user.username,
                             audit.trx_id, audit.block_id]
                        )
                    except VoteAudit.DoesNotExist:
                        data.add_row(
                            [choice.text, user.username, 'missing', 'missing']
                        )

        return HttpResponse(f"<pre>{data}</pre>")

    return render(request, "poll_detail.html", {
        "poll": poll,
        "choices": choice_list,
        "sorted_choices": sorted_choice_list,
        "total_votes": all_votes,
        "user_votes": user_votes,
        "all_votes": all_votes,
        "show_bars": selected_different_choices > 1,
        "filters_applied": needs_filtering,
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

    if poll.allow_multiple_choices:
        choice_ids = request.POST.getlist("choice-id")
    else:
        choice_ids = [request.POST.get("choice-id"),]
    additional_thoughts = request.POST.get("vote-comment", "")

    if not choice_ids:
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

    for choice_id in choice_ids:
        try:
            choice = Choice.objects.get(pk=int(choice_id))
        except Choice.DoesNotExist:
            raise Http404

    choice_instances = []
    for choice_id in choice_ids:
        choice = Choice.objects.get(pk=int(choice_id))
        choice_instances.append(choice)

    # send it to the steem blockchain
    sc_client = Client(access_token=request.session.get("sc_token"))
    choice_text = ",".join([c.text.strip() for c in choice_instances])
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
            "votes": [c.text.strip() for c in choice_instances],
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

    # Steemconnect sometimes returns 503.
    # https://github.com/steemscript/steemconnect/issues/356
    if not isinstance(resp, dict):
        messages.add_message(
            request,
            messages.ERROR,
            "We got an unexpected error from Steemconnect. Please, try again."
        )
        return redirect("detail", poll.username, poll.permlink)

    # Expected way to receive errors on broadcasting
    if 'error' in resp:
        messages.add_message(
            request,
            messages.ERROR,
            resp.get("error_description", "error")
        )

        return redirect("detail", poll.username, poll.permlink)

    # register the vote to the database
    for choice_instance in choice_instances:
        choice_instance.voted_users.add(request.user)

    block_id = resp.get("result", {}).get("block_num")
    trx_id = resp.get("result", {}).get("id")

    # add trx id and block id to the audit log
    vote_audit = VoteAudit(
        question=poll,
        voter=request.user,
        block_id=block_id,
        trx_id=trx_id
    )
    vote_audit.save()
    for choice_instance in choice_instances:
        vote_audit.choices.add(choice_instance)

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
        already_counted_users = []
        for choice in question.choices.all():
            voted_users = choice.voted_users.all()
            for voted_user in voted_users:
                if voted_user.pk in already_counted_users:
                    continue
                vote_count += 1
                # now, with the multiple choices implemented
                # only one choice of a user should be counted, here.
                already_counted_users.append(voted_user.pk)
        polls.append({"vote_count": vote_count, "poll": question})

    polls = sorted(polls, key=lambda x: x["vote_count"], reverse=True)

    return render(request, "polls_by_vote.html", {
        "polls": polls, "start_time": start_time, "end_time": end_time})
