import sip
sip.setapi('QString', 2)
import src._replace as rep
reload(rep)
Window = rep.Window