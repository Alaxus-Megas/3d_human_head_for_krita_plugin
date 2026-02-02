from .free_3dhead import Free3DHeadDockerFactory
import krita


app = krita.Krita.instance()


extension = Free3DHeadDockerFactory()
app.addDockWidgetFactory(extension)