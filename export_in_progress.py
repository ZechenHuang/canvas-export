# built in
import json
import os
import string

# external
from canvasapi import Canvas
from canvasapi.exceptions import ResourceDoesNotExist
import dateutil.parser
import jsonpickle
import requests
import yaml
import time

#This project gets information from Canvas LMS system and saved as files.
#This files is modified by Zechen from David(davekats)'s project https://github.com/davekats/canvas-student-data-export
#I modified this program to use in Windows system, and specific courses.
#To see how to use canvas api, go to https://canvasapi.readthedocs.io/en/stable/getting-started.html
try:
    with open("credentials.yaml", 'r') as f:
        credentials = yaml.load(f)
except OSError:
    # Canvas API URL
    API_URL = ""
    # Canvas API key
    API_KEY = ""
    # My Canvas User ID
    USER_ID = 0
else:
    API_URL = credentials["API_URL"]
    API_KEY = credentials["API_KEY"]
    USER_ID = credentials["USER_ID"]

# Directory in which to download course information to (will be created if not
# present)
DL_LOCATION = "C:\\output" #I use this in windows, so it's a C: 
# List of Course IDs that should be skipped (need to be integers)
COURSES_TO_SKIP = []

DATE_TEMPLATE = "%B %d, %Y %I:%M %p"


class moduleItemView():
    title = ""
    content_type = ""
    external_url = ""


class moduleView():
    name = ""
    items = []

    def __init__(self):
        self.items = []


class pageView():
    title = ""
    body = ""
    created_date = ""
    last_updated_date = ""


class topicReplyView():
    author = ""
    posted_date = ""
    body = ""


class topicEntryView():
    author = ""
    posted_date = ""
    body = ""
    topic_replies = []

    def __init__(self):
        self.topic_replies = []


class discussionView():
    title = ""
    author = ""
    posted_date = ""
    body = ""
    topic_entries = []

    def __init__(self):
        self.topic_entries = []


class submissionView():
    attachments = []
    grade = ""
    raw_score = ""
    submission_comments = ""
    total_possible_points = ""
    user_id = "no-id"

    def __init__(self):
        self.attachments = []
        self.grade = ""
        self.raw_score = ""
        self.submission_comments = ""
        self.total_possible_points = ""
        self.user_id = None  # integer


class attachmentView():
    filename = ""
    id = 0
    url = ""

    def __init__(self):
        self.filename = ""
        self.id = 0
        self.url = ""


class assignmentView():
    title = ""
    description = ""
    assigned_date = ""
    due_date = ""
    submission = None
    submissions = []

    def __init__(self):
        self.submission = submissionView()
        self.submissions = []


class courseView():
    term = ""
    course_code = ""
    name = ""
    assignments = []
    announcements = []
    discussions = []

    def __init__(self):
        self.assignments = []
        self.announcements = []
        self.discussions = []


def makeValidFilename(input_str):
    # Remove invalid characters
    valid_chars = "-_.() %s%s" % (string.ascii_letters, string.digits)
    input_str = "".join(c for c in input_str if c in valid_chars)

    # Remove leading and trailing whitespace
    input_str = input_str.lstrip().rstrip()

    return input_str


def findCourseModules(course, course_view):
    #for some courses, they contains invlid character as a file name in windows, so replace those character to '-'
    modules_dir = os.path.join(DL_LOCATION, str(course_view.term).replace(':','-').replace(' ','-').replace('?','-'),
                               str(course_view.course_code).replace(':','-').replace(' ','-').replace('?','-'), "modules")

    # Create modules directory if not present
    if not os.path.exists(modules_dir):
        os.makedirs(modules_dir)

    module_views = []

    try:
        modules = course.get_modules()

        for module in modules:
            module_view = moduleView()

            # Name
            module_view.name = str(module.name) if hasattr(module, "name") else ""

            try:
                # Get module items
                module_items = module.get_module_items()
                #this is for some files that have sames names
                count_for_duplicated=0

                for module_item in module_items:
                    module_item_view = moduleItemView()

                    # Title
                    module_item_view.title = str(module_item.title) if hasattr(module_item, "title") else ""

                    # Type
                    module_item_view.content_type = str(module_item.type) if hasattr(module_item, "type") else ""

                    # External URL
                    module_item_view.external_url = str(module_item.external_url) if hasattr(module_item, "external_url") else ""

                    if module_item_view.content_type == "File":
                        module_dir = modules_dir + "/" + makeValidFilename(str(module.name).replace(':','-').replace(' ','-'))

                        try:
                            # Create directory for current module if not present
                            if not os.path.exists(module_dir):
                                os.makedirs(module_dir)

                            # Get the file object
                            module_file = course.get_file(str(module_item.content_id))

                            # Create path for module file download
                            module_file_path = module_dir + "/" + makeValidFilename(str(module_file.display_name).replace(':','-').replace(' ','-'))

                            # Download file if it doesn't already exist
                            if not os.path.exists(module_file_path):
                                print('Downloading modules: {}'.format(module_file_path))
                                module_file.download(module_file_path)
                            else:
                                #If there are files have same name, add numbers after
                                module_file_path =module_file_path+ "("+str(count_for_duplicated)+")"
                                count_for_duplicated += 1
                                module_file.download(module_file_path)
                                print('File already exists: {}'.format(module_file_path))
                            #Some time remote server will refuse after so many connections, so add sleep to avoid that.
                            time.sleep(2)

                        except Exception as e:
                            print("Skipping module file download that gave the following error:")
                            print(e)

                    module_view.items.append(module_item_view)
            except Exception as e:
                print("Skipping module item that gave the following error:")
                print(e)

            module_views.append(module_view)

    except Exception as e:
        print("Skipping entire module that gave the following error:")
        print(e)

    return module_views


def downloadCourseFiles(course, course_view):
    #same reason that we need to replace the invalid character in Windows system
    dl_dir = os.path.join(DL_LOCATION, str(course_view.term).replace(':','-').replace(' ','-').replace('?','-'),
                          str(course_view.course_code).replace(':','-').replace(' ','-').replace('?','-'), "files")

    # Create directory if not present
    if not os.path.exists(dl_dir):
        os.makedirs(dl_dir)

    try:
        files = course.get_files()
        count_for_duplicated=0
        for file in files:
            dl_path = os.path.join(dl_dir,
                                   makeValidFilename(str(file.display_name)))

            # Download file if it doesn't already exist
            if not os.path.exists(dl_path):
                print('Downloading: {}'.format(dl_path))
                file.download(dl_path)
            else:
                dl_path = dl_path + "("+str(count_for_duplicated)+")"
                count_for_duplicated += 1
                file.download(dl_path)
                print('File already exists: {}'.format(dl_path))
            #sleep to avoid refusion
            time.sleep(2)

    except Exception as e:
        print("Skipping file download that gave the following error:")
        print(e)


def download_submission_attachments(course, course_view):
    #same reason that we need to replace the invalid character in Windows system
    course_dir = os.path.join(DL_LOCATION, str(course_view.term).replace(':','-').replace(' ','-').replace('?','-'),
                              str(course_view.course_code).replace(':','-').replace(' ','-').replace('?','-'))

    # Create directory if not present
    if not os.path.exists(course_dir):
        os.makedirs(course_dir)

    for assignment in course_view.assignments:
        #sleep to avoid refusion
        time.sleep(2)
        #David's code was trying to download all submission for this course, but it is not working for students. Students are only
        #allowed to download their own submission.
        submission = assignment.submission
        attachment_dir = os.path.join(course_dir, str(assignment.title).replace(':','-').replace(' ','-').replace('?','-'))
        if not os.path.exists(attachment_dir):
            os.makedirs(attachment_dir)
        for attachment in submission.attachments:
            filepath = os.path.join(attachment_dir, str(attachment.id) +
                                    "_" + attachment.filename)
            if not os.path.exists(filepath):
                print('Downloading attachment: {}'.format(filepath))
                r = requests.get(attachment.url, allow_redirects=True)
                with open(filepath, 'wb') as f:
                    f.write(r.content)
            else:
                print('File already exists: {}'.format(filepath))


def getCoursePageUrls(course):
    page_urls = []

    try:
        # Get all pages
        pages = course.get_pages()

        for page in pages:
            if hasattr(page, "url"):
                page_urls.append(str(page.url))
    except Exception as e:
        if e.message != "Not Found":
            print("Skipping page that gave the following error:")
            print(e)

    return page_urls


def findCoursePages(course):
    page_views = []

    try:
        # Get all page URLs
        page_urls = getCoursePageUrls(course)

        for url in page_urls:
            page = course.get_page(url)

            page_view = pageView()

            # Title
            page_view.title = str(page.title) if hasattr(page, "title") else ""
            # Body
            page_view.body = str(page.body) if hasattr(page, "body") else ""
            # Date created
            if hasattr(page, "created_at"):
                page_view.created_date = dateutil.parser.parse(
                    page.created_at).strftime(DATE_TEMPLATE)
            else:
                page_view.created_date = ""
            # Date last updated
            if hasattr(page, "updated_at"):
                page_view.last_updated_date = dateutil.parser.parse(
                    page.updated_at).strftime(DATE_TEMPLATE)
            else:
                page_view.last_updated_date = ""

            page_views.append(page_view)
    except Exception as e:
        print("Skipping page download that gave the following error:")
        print(e)

    return page_views


def findCourseAssignments(course):
    assignment_views = []

    # Get all assignments
    assignments = course.get_assignments()
    
    try:
        for assignment in assignments:
            # Create a new assignment view
            assignment_view = assignmentView()

            # Title
            if hasattr(assignment, "name"):
                assignment_view.title = str(assignment.name)
            else:
                assignment_view.title = ""
            # Description
            if hasattr(assignment, "description"):
                assignment_view.description = str(assignment.description)
            else:
                assignment_view.description = ""
            # Assigned date
            if hasattr(assignment, "created_at_date"):
                assignment_view.assigned_date = assignment.created_at_date.strftime(DATE_TEMPLATE)
            else:
                assignment_view.assigned_date = ""
            # Due date
            if hasattr(assignment, "due_at_date"):
                assignment_view.due_date = assignment.due_at_date.strftime(DATE_TEMPLATE)
            else:
                assignment_view.due_date = ""

            # Download all submissions
            try:
                submissions = assignment.get_submissions()
            # TODO : Figure out the exact error raised
            except:
                print("Got no submissions for this assignment")
            else:
                try:
                    for submission in submissions:

                        sub_view = submissionView()

                        # My grade
                        if hasattr(submission, "grade"):
                            sub_view.grade = str(submission.grade)
                        else:
                            sub_view.grade = ""
                        # My raw score
                        if hasattr(submission, "score"):
                            sub_view.raw_score = str(submission.score)
                        else:
                            sub_view.raw_score = ""
                        # Total possible score
                        if hasattr(assignment, "points_possible"):
                            sub_view.total_possible_points = str(assignment.points_possible)
                        else:
                            sub_view.total_possible_points = ""
                        # Submission comments
                        if hasattr(submission, "submission_comments"):
                            sub_view.submission_comments = str(submission.submission_comments)
                        else:
                            sub_view.submission_comments = ""

                        if hasattr(submission, "user_id"):
                            sub_view.user_id = str(submission.user_id)
                        else:
                            sub_view.user_id = "no-id"

                        try:
                            submission.attachments
                        except AttributeError:
                            print('No attachments')
                        else:
                            for attachment in submission.attachments:
                                attach_view = attachmentView()
                                attach_view.url = attachment["url"]
                                attach_view.id = attachment["id"]
                                attach_view.filename = attachment["filename"]
                                sub_view.attachments.append(attach_view)
                        assignment_view.submissions.append(sub_view)
                except Exception as e:
                    print(" ")
                    #print("Skipping submission that gave the following error:")
                    #print(e)

            # The following is only useful if you are a student in the class.
            # Get my user"s submission object
            try:
                submission = assignment.get_submission(USER_ID)
            except ResourceDoesNotExist:
                print('No submission for user: {}'.format(USER_ID))
            else:
                # Create a new submission view
                assignment_view.submission = submissionView()

                # My grade
                assignment_view.submission.grade = str(submission.grade) if hasattr(submission, "grade") else ""
                # My raw score
                assignment_view.submission.raw_score = str(submission.score) if hasattr(submission, "score") else ""
                # Total possible score
                assignment_view.submission.total_possible_points = str(assignment.points_possible) if hasattr(assignment, "points_possible") else ""
                # Submission comments
                assignment_view.submission.submission_comments = str(submission.submission_comments) if hasattr(submission, "submission_comments") else ""
                try:
                    attach = submission.attachments
                    for attachment in attach:
                        attach_view = attachmentView()
                        attach_view.url = attachment["url"]
                        attach_view.id = attachment["id"]
                        attach_view.filename = attachment["filename"]
                        assignment_view.submission.attachments.append(attach_view)
                except Exception as e:
                    print(e)
                
                    
            assignment_views.append(assignment_view)
    except Exception as e:
        print("Skipping course assignments that gave the following error:")
        print(e)

    return assignment_views


def findCourseAnnouncements(course):
    announcement_views = []

    try:
        announcements = course.get_discussion_topics(only_announcements=True)

        for announcement in announcements:
            discussion_view = getDiscussionView(announcement)

            announcement_views.append(discussion_view)
    except Exception as e:
        print("Skipping announcement that gave the following error:")
        print(e)

    return announcement_views


def getDiscussionView(discussion_topic):
    # Create discussion view
    discussion_view = discussionView()

    # Title
    discussion_view.title = str(discussion_topic.title) if hasattr(discussion_topic, "title") else ""
    # Author
    discussion_view.author = str(discussion_topic.user_name) if hasattr(discussion_topic, "user_name") else ""
    # Posted date
    discussion_view.posted_date = discussion_topic.created_at_date.strftime("%B %d, %Y %I:%M %p") if hasattr(discussion_topic, "created_at_date") else ""
    # Body
    discussion_view.body = str(discussion_topic.message) if hasattr(discussion_topic, "message") else ""
    # Topic entries
    if hasattr(discussion_topic, "discussion_subentry_count") and discussion_topic.discussion_subentry_count > 0:
        # Need to get replies to entries recursively?

        discussion_topic_entries = discussion_topic.get_topic_entries()

        try:
            for topic_entry in discussion_topic_entries:
                # Create new discussion view for the topic_entry
                topic_entry_view = topicEntryView()

                # Author
                topic_entry_view.author = str(topic_entry.user_name) if hasattr(topic_entry, "user_name") else ""
                # Posted date
                topic_entry_view.posted_date = topic_entry.created_at_date.strftime("%B %d, %Y %I:%M %p") if hasattr(topic_entry, "created_at_date") else ""
                # Body
                topic_entry_view.body = str(topic_entry.message) if hasattr(topic_entry, "message") else ""

                # Get this topic's replies
                topic_entry_replies = topic_entry.get_replies()

                try:
                    for topic_reply in topic_entry_replies:
                        # Create new topic reply view
                        topic_reply_view = topicReplyView()

                        # Author
                        topic_reply_view.author = str(topic_reply.user_name) if hasattr(topic_reply, "user_name") else ""
                        # Posted Date
                        topic_reply_view.posted_date = topic_reply.created_at_date.strftime("%B %d, %Y %I:%M %p") if hasattr(topic_reply, "created_at_date") else ""
                        # Body
                        topic_reply_view.message = str(topic_reply.message) if hasattr(topic_reply, "message") else ""

                        topic_entry_view.topic_replies.append(topic_reply_view)
                except Exception as e:
                    print("Tried to enumerate discussion topic entry replies but received the following error:")
                    print(e)

                discussion_view.topic_entries.append(topic_entry_view)
        except Exception as e:
            print("Tried to enumerate discussion topic entries but received the following error:")
            print(e)

    return discussion_view


def findCourseDiscussions(course):
    discussion_views = []

    try:
        discussion_topics = course.get_discussion_topics()

        for discussion_topic in discussion_topics:
            discussion_view = None
            discussion_view = getDiscussionView(discussion_topic)

            discussion_views.append(discussion_view)
    except Exception as e:
        print("Skipping discussion that gave the following error:")
        print(e)

    return discussion_views


def getCourseView(course):
    course_view = courseView()

    # Course term
    course_view.term = course.term["name"] if hasattr(course, "term") and "name" in course.term.keys() else ""

    # Course code
    course_view.course_code = course.course_code if hasattr(course, "course_code") else ""

    # Course name
    course_view.name = course.name if hasattr(course, "name") else ""

    print("Working on " + course_view.term + ": " + course_view.name)

    # Course assignments
    print("  Getting assignments")
    course_view.assignments = findCourseAssignments(course)

    # Course announcements
    print("  Getting announcements")
    course_view.announcements = findCourseAnnouncements(course)

    # Course discussions
    print("  Getting discussions")
    course_view.discussions = findCourseDiscussions(course)

    # Course pages
    print("  Getting pages")
    course_view.pages = findCoursePages(course)

    return course_view


def exportAllCourseData(course_view):
    json_str = json.dumps(json.loads(jsonpickle.encode(course_view, unpicklable = False)), indent = 4)

    course_output_dir = os.path.join(DL_LOCATION, str(course_view.term).replace(':','-').replace(' ','-').replace('?','-'),
                                     str(course_view.course_code).replace(':','-').replace(' ','-').replace('?','-'))

    # Create directory if not present
    if not os.path.exists(course_output_dir):
        os.makedirs(course_output_dir)

    course_output_path = os.path.join(course_output_dir,
                                      course_view.course_code + ".json")

    with open(course_output_path, "w") as out_file:
        out_file.write(json_str)


if __name__ == "__main__":

    print("Welcome to the Canvas Student Data Export Tool\n")

    if API_URL == "":
        # Canvas API URL
        print("We will need your organization's Canvas Base URL. This is "
              "probably something like https://{schoolName}.instructure.com)")
        API_URL = input("Enter your organization's Canvas Base URL: ")

    if API_KEY == "":
        # Canvas API key
        print("\nWe will need a valid API key for your user. You can generate "
              "one in Canvas once you are logged in.")
        API_KEY = input("Enter a valid API key for your user: ")

    if USER_ID == 0000000:
        # My Canvas User ID
        print("\nWe will need your Canvas User ID. You can find this by "
              "logging in to canvas and then going to this URL in the same "
              "browser {yourCanvasBaseUrl}/api/v1/users/self")
        USER_ID = input("Enter your Canvas User ID: ")

    print("\nConnecting to canvas\n")

    # Initialize a new Canvas object
    canvas = Canvas(API_URL, API_KEY)

    print("Creating output directory: " + DL_LOCATION + "\n")
    # Create directory if not present
    if not os.path.exists(DL_LOCATION):
        os.makedirs(DL_LOCATION)

    all_courses_views = []

    print("Getting list of all courses\n")

    #Modified this array for the courses id you want to download.
    #I am lazy so modify the code yourself. :-)
    #If you like, you can make this as a input stream.
    #Course id can found by website. 
    #For example, https://canvas.iastate.edu/courses/31798, 31798 is the course id.
    all_I_need =[]


    for i in all_I_need:
        course = canvas.get_course(i)

        course_view = getCourseView(course)

        all_courses_views.append(course_view)

        print("  Downloading all files")
        downloadCourseFiles(course, course_view)

        print("  Downloading submission attachments")
        download_submission_attachments(course, course_view)

        print("  Getting modules and downloading module files")
        course_view.modules = findCourseModules(course, course_view)

        print("  Exporting all course data")
        exportAllCourseData(course_view)
        #same reason for a little break
        time.sleep(20)

    print("Exporting data from all courses combined as one file: "
          "all_output.json")


    # Awful hack to make the JSON pretty. Decode it with Python stdlib json
    # module then re-encode with indentation
    json_str = json.dumps(json.loads(jsonpickle.encode(all_courses_views,
                                                       unpicklable=False)),
                          indent=4)

    all_output_path = os.path.join(DL_LOCATION, "all_output.json")

    with open(all_output_path, "w") as out_file:
        out_file.write(json_str)

    print("\nProcess complete. All canvas data exported!")