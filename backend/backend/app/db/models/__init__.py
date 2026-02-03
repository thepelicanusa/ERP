from .common import *  # noqa
from .auth import *  # noqa
from .inventory import *  # noqa
from .sales import *  # noqa
from .purchasing import *  # noqa
from .accounting import *  # noqa
from .qms import *  # noqa
from .mrp import *  # noqa
from .docs import *  # noqa
# from .mes import *  # noqa
from .inventory_exec import *  # noqa
from .system_modules import *  # noqa
from .security_audit import *  # noqa
from .iam_tokens import *  # noqa
from .mes_exec import *  # noqa
from .planning import *  # noqa
from .fin_close import *  # noqa
from .genealogy import *  # noqa

from .email_engine import *  # noqa

from .crm import *  # noqa

from .employee import *  # noqa

from .ecommerce import *  # noqa

from .mdm import *  # noqa

# Platform event-bus tables (transactional outbox + webhook subscriptions)
from app.events.outbox import *  # noqa
from app.events.subscriptions import *  # noqa

from app.db.models.contacts import *  # noqa: F401,F403
from app.db.models.support import *  # noqa: F401,F403
