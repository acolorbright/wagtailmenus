from django.conf.urls import url
from django.contrib.admin.utils import quote
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _

from wagtail.contrib.modeladmin.options import ModelAdmin, modeladmin_register
from wagtail.contrib.modeladmin.helpers import ButtonHelper
from wagtail.wagtailcore import hooks

from .app_settings import (
    MAINMENU_MENU_ICON, FLATMENU_MENU_ICON, SECTION_ROOT_DEPTH)
from .models import MainMenu, FlatMenu
from .views import (
    MainMenuIndexView, MainMenuEditView, FlatMenuCopyView)


class MainMenuAdmin(ModelAdmin):
    model = MainMenu
    menu_label = _('Main menu')
    menu_icon = MAINMENU_MENU_ICON
    index_view_class = MainMenuIndexView
    edit_view_class = MainMenuEditView
    add_to_settings_menu = True

    def get_admin_urls_for_registration(self):
        return (
            url(self.url_helper.get_action_url_pattern('index'),
                self.index_view,
                name=self.url_helper.get_action_url_name('index')),
            url(self.url_helper.get_action_url_pattern('edit'),
                self.edit_view,
                name=self.url_helper.get_action_url_name('edit')),
        )


class FlatMenuButtonHelper(ButtonHelper):

    def copy_button(self, pk, classnames_add=[], classnames_exclude=[]):
        cn = self.finalise_classname(classnames_add, classnames_exclude)
        return {
            'url': self.url_helper.get_action_url('copy', quote(pk)),
            'label': _('Copy'),
            'classname': cn,
            'title': _('Copy this %s') % self.verbose_name,
        }

    def get_buttons_for_obj(self, obj, exclude=[], classnames_add=[],
                            classnames_exclude=[]):
        ph = self.permission_helper
        usr = self.request.user
        pk = quote(getattr(obj, self.opts.pk.attname))
        btns = super(FlatMenuButtonHelper, self).get_buttons_for_obj(
            obj, exclude, classnames_add, classnames_exclude)
        if('copy' not in exclude and ph.user_can_create(usr)):
            btns.append(
                self.copy_button(pk, classnames_add, classnames_exclude)
            )
        return btns


class FlatMenuAdmin(ModelAdmin):
    model = FlatMenu
    menu_label = _('Flat menus')
    menu_icon = FLATMENU_MENU_ICON
    button_helper_class = FlatMenuButtonHelper
    ordering = ('-site__is_default_site', 'site__hostname', 'handle')
    add_to_settings_menu = True

    def copy_view(self, request, instance_pk):
        kwargs = {'model_admin': self, 'instance_pk': instance_pk}
        return FlatMenuCopyView.as_view(**kwargs)(request)

    def get_admin_urls_for_registration(self):
        urls = super(FlatMenuAdmin, self).get_admin_urls_for_registration()
        urls += (
            url(self.url_helper.get_action_url_pattern('copy'),
                self.copy_view,
                name=self.url_helper.get_action_url_name('copy')),
        )
        return urls

    def get_list_filter(self, request):
        if self.is_multisite_listing(request):
            return ('site', 'handle')
        return ()

    def get_list_display(self, request):
        if self.is_multisite_listing(request):
            return ('title', 'handle_formatted', 'site', 'items')
        return ('title', 'handle_formatted', 'items')

    def handle_formatted(self, obj):
        return mark_safe('<code>%s</code>' % obj.handle)
    handle_formatted.short_description = 'handle'
    handle_formatted.admin_order_field = 'handle'

    def is_multisite_listing(self, request):
        return self.get_queryset(request).values('site').distinct().count() > 1

    def items(self, obj):
        return obj.menu_items.count()
    items.short_description = _('no. of items')


modeladmin_register(FlatMenuAdmin)


@hooks.register('before_serve_page')
def wagtailmenu_params_helper(page, request, serve_args, serve_kwargs):
    section_root = request.site.root_page.get_descendants().ancestor_of(
        page, inclusive=True).filter(depth__exact=SECTION_ROOT_DEPTH).first()
    if section_root:
        section_root = section_root.specific
    ancestor_ids = page.get_ancestors().values_list('id', flat=True)
    request.META.update({
        'CURRENT_SECTION_ROOT': section_root,
        'CURRENT_PAGE_ANCESTOR_IDS': ancestor_ids,
    })
