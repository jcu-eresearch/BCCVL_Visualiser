from pyramid.response import Response
from pyramid.view import view_config
from pyramid.i18n import get_localizer

from zope.interface import Interface, Attribute, implements

from sqlalchemy.exc import DBAPIError

from bccvl_visualiser.models import (
    DBSession,
    Species,
    Occurrence,
    )

class IView(Interface):

    #: The title of the view. This is displayed in breadcrumbs and page titles.
    Title = Attribute('The title of a view')
    description = Attribute('Description of a view to be displayed')

    def __init__(context, request):
        """Initialisation function for a given view.
        """
        pass

    def __call__():
        """Run view and return a response or something to render to response.
        """
        pass

class BaseView(object):
    """Base Class for all subsequent views"""
    implements(IView)

    Title = None
    description = None

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.localizer = get_localizer(request)
        self.dbsession = DBSession

    def __call__(self):
        values = {
            'localizer': self.localizer
        }

        return values

@view_config(route_name='home', renderer='../templates/mytemplate.pt')
def my_view(request):
    try:
        one = DBSession.query(Species).filter(Species.name == 'one').first()
    except DBAPIError:
        return Response(conn_err_msg, content_type='text/plain', status_int=500)
    return {'one': one, 'project': 'BCCVL_Visualiser'}

#def species_search_result(request):
#    return {'one': one, 'project': 'WebApp'}

conn_err_msg = """\
Pyramid is having a problem using your SQL database.  The problem
might be caused by one of the following things:

1.  You may need to run the "initialize_WebApp_db" script
    to initialize your database tables.  Check your virtual 
    environment's "bin" directory for this script and try to run it.

2.  Your database server may not be running.  Check that the
    database server referred to by the "sqlalchemy.url" setting in
    your "development.ini" file is running.

After you fix the problem, please restart the Pyramid application to
try it again.
"""

