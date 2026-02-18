<?php
/**
 * Plugin Name: D2CMS Dev Token Auth
 * Description: Minimal utility to inject bearer token auth into WordPress.
 */

add_filter('determine_current_user', function($userId) {
    $devToken = getDevToken();
    $devUser = getDevUser();

    error_log("TOKEN IS: " . $devToken);
    error_log("USER IS: " . $devUser);

    if (!$devToken) {
        return $userId;
    }

    $header = $_SERVER['HTTP_AUTHORIZATION'] ?? '';
    if (strpos($header, 'Bearer') !== 0) {
        error_log("BEARER AUTH IS NOT THERE");
        return $userId;
    }

    $providedToken = trim(substr($header, 7));
    error_log("PROVIDED TOKEN IS: " . $providedToken);
    if (!hash_equals($devToken, $providedToken)) {
        error_log("HASH IS WRONG");
        return $userId;
    }

    $user = get_user_by('login', $devUser);

    error_log("USER IS: " . $user->name);

    return !$user ? $userId : (int) $user -> ID;
}, 20);

function getDevUser() {
    return getenv('D2CMS_WP_API_USER');
}

function getDevToken() {
    return getenv('D2CMS_WP_DEV_TOKEN');
}