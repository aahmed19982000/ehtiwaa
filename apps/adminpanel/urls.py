from django.urls import path

from . import views

app_name = "adminpanel"

urlpatterns = [
    path("login/", views.PanelLoginView.as_view(), name="panel-login"),
    path("", views.DashboardOverviewView.as_view(), name="dashboard"),
    # Specialists
    path("specialists/", views.SpecialistListView.as_view(), name="specialists"),
    path("specialists/create/", views.SpecialistCreateView.as_view(), name="specialist-create"),
    path("specialists/<int:pk>/edit/", views.SpecialistUpdateView.as_view(), name="specialist-edit"),
    path("specialists/<int:pk>/delete/", views.SpecialistDeleteView.as_view(), name="specialist-delete"),
    path(
        "specialists/<int:pk>/toggle-featured/",
        views.SpecialistToggleFeaturedView.as_view(),
        name="specialist-toggle-featured",
    ),
    path("specialists/<int:pk>/approve/", views.SpecialistApproveView.as_view(), name="specialist-approve"),
    path("specialists/<int:pk>/reject/", views.SpecialistRejectView.as_view(), name="specialist-reject"),
    # Courses
    path("courses/", views.CourseListView.as_view(), name="courses"),
    path("courses/create/", views.CourseCreateView.as_view(), name="course-create"),
    path("courses/<int:pk>/edit/", views.CourseUpdateView.as_view(), name="course-edit"),
    path("courses/<int:pk>/delete/", views.CourseDeleteView.as_view(), name="course-delete"),
    path(
        "courses/<int:pk>/toggle-featured/",
        views.CourseToggleFeaturedView.as_view(),
        name="course-toggle-featured",
    ),
    path("courses/<int:pk>/curriculum/", views.CourseCurriculumView.as_view(), name="course-curriculum"),
    path("courses/<int:pk>/modules/create/", views.ModuleCreateView.as_view(), name="module-create"),
    path("courses/modules/<int:pk>/edit/", views.ModuleUpdateView.as_view(), name="module-edit"),
    path("courses/modules/<int:pk>/delete/", views.ModuleDeleteView.as_view(), name="module-delete"),
    path(
        "courses/modules/<int:pk>/lessons/create/",
        views.LessonCreateView.as_view(),
        name="lesson-create",
    ),
    path("courses/lessons/<int:pk>/edit/", views.LessonUpdateView.as_view(), name="lesson-edit"),
    path("courses/lessons/<int:pk>/delete/", views.LessonDeleteView.as_view(), name="lesson-delete"),
    # Articles
    path("articles/", views.ArticleListView.as_view(), name="articles"),
    path("articles/create/", views.ArticleCreateView.as_view(), name="article-create"),
    path("articles/<int:pk>/edit/", views.ArticleUpdateView.as_view(), name="article-edit"),
    path("articles/<int:pk>/delete/", views.ArticleDeleteView.as_view(), name="article-delete"),
    path("articles/upload-image/", views.ArticleImageUploadView.as_view(), name="article-upload-image"),
    path("articles/translate/", views.ArticleTranslateView.as_view(), name="article-translate"),
    path(
        "articles/<int:pk>/review/approve/",
        views.ArticleReviewApproveView.as_view(),
        name="article-review-approve",
    ),
    path(
        "articles/<int:pk>/review/reject/",
        views.ArticleReviewRejectView.as_view(),
        name="article-review-reject",
    ),
    path("articles/categories/", views.CategoryListView.as_view(), name="categories"),
    path("articles/categories/create/", views.CategoryCreateView.as_view(), name="category-create"),
    path("articles/categories/<int:pk>/edit/", views.CategoryUpdateView.as_view(), name="category-edit"),
    path(
        "articles/categories/<int:pk>/delete/", views.CategoryDeleteView.as_view(), name="category-delete"
    ),
    # Videos
    path("videos/", views.VideoListView.as_view(), name="videos"),
    path("videos/create/", views.VideoCreateView.as_view(), name="video-create"),
    path("videos/<int:pk>/edit/", views.VideoUpdateView.as_view(), name="video-edit"),
    path("videos/<int:pk>/delete/", views.VideoDeleteView.as_view(), name="video-delete"),
    path(
        "videos/<int:pk>/toggle-featured/",
        views.VideoToggleFeaturedView.as_view(),
        name="video-toggle-featured",
    ),
    # Homepage: hero + banners + testimonials
    path("homepage/", views.HomepageContentView.as_view(), name="homepage"),
    path("homepage/banners/", views.BannerListView.as_view(), name="banners"),
    path("homepage/banners/create/", views.BannerCreateView.as_view(), name="banner-create"),
    path("homepage/banners/<int:pk>/edit/", views.BannerUpdateView.as_view(), name="banner-edit"),
    path("homepage/banners/<int:pk>/delete/", views.BannerDeleteView.as_view(), name="banner-delete"),
    path("homepage/testimonials/", views.TestimonialListView.as_view(), name="testimonials"),
    path(
        "homepage/testimonials/create/", views.TestimonialCreateView.as_view(), name="testimonial-create"
    ),
    path(
        "homepage/testimonials/<int:pk>/edit/",
        views.TestimonialUpdateView.as_view(),
        name="testimonial-edit",
    ),
    path(
        "homepage/testimonials/<int:pk>/delete/",
        views.TestimonialDeleteView.as_view(),
        name="testimonial-delete",
    ),
    path(
        "homepage/specialty-tags/create/",
        views.SpecialtyTagCreateView.as_view(),
        name="specialty-tag-create",
    ),
    path(
        "homepage/specialty-tags/<int:pk>/delete/",
        views.SpecialtyTagDeleteView.as_view(),
        name="specialty-tag-delete",
    ),
    # Users / Bookings / Payments / Reports
    path("payments/", views.PaymentsListView.as_view(), name="payments"),
    path("users/", views.UsersListView.as_view(), name="users"),
    path("bookings/", views.BookingsListView.as_view(), name="bookings"),
    path("reports/", views.ReportsView.as_view(), name="reports"),
    # Roles & permissions
    path("roles/", views.RoleListView.as_view(), name="roles"),
    path("roles/create/", views.RoleCreateView.as_view(), name="role-create"),
    path("roles/<int:pk>/edit/", views.RoleUpdateView.as_view(), name="role-edit"),
    path("roles/<int:pk>/delete/", views.RoleDeleteView.as_view(), name="role-delete"),
    # Admins
    path("roles/admins/", views.AdminsListView.as_view(), name="admins"),
    path("roles/admins/create/", views.AdminCreateView.as_view(), name="admin-create"),
    path("roles/admins/<int:pk>/edit/", views.AdminUpdateView.as_view(), name="admin-edit"),
    path("roles/admins/<int:pk>/assign/", views.AdminAssignRoleView.as_view(), name="admin-assign-role"),
]
